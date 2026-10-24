"""
Tests for PhysicsComputeSynergyRouter (PCSR - Custom Proposed Strategy).
"""

from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.physics_compute_synergy import PhysicsComputeSynergyRouter
from skynetra.foundation.types import NodeId


def _make_packet(src: str, dst: str, pkt_type: str = "data") -> Packet:
    return Packet(
        packet_id="pkt-pcsr",
        src=NodeId(src),
        dst=NodeId(dst),
        size_bytes=1000,
        packet_type=pkt_type,
        created_at=0.0,
    )


def _build_synergy_graph() -> tuple[nx.DiGraph, dict[NodeId, RelayNode | PodNode]]:
    """Topology with two alternate paths to compute destination:
    src -> sat_p0_s1 -> pod_1 (path 1: delay 4ms, 100 Gbps)
    src -> sat_p0_s2 -> pod_2 (path 2: delay 5ms, 100 Gbps)
    """
    g = nx.DiGraph()
    registry: dict[NodeId, RelayNode | PodNode] = {
        NodeId("src"): RelayNode(NodeId("src")),
        NodeId("sat_p0_s1"): RelayNode(NodeId("sat_p0_s1")),
        NodeId("sat_p0_s2"): RelayNode(NodeId("sat_p0_s2")),
        NodeId("pod_1"): PodNode(NodeId("pod_1"), flops=1e12),
        NodeId("pod_2"): PodNode(NodeId("pod_2"), flops=1e12),
    }
    for nid, node in registry.items():
        g.add_node(nid, node_type=node.node_type)

    g.add_edge(NodeId("src"), NodeId("sat_p0_s1"), propagation_delay_ms=2.0, capacity=100.0, link_type="isl")
    g.add_edge(NodeId("sat_p0_s1"), NodeId("pod_1"), propagation_delay_ms=2.0, capacity=10.0, link_type="pod")
    g.add_edge(NodeId("src"), NodeId("sat_p0_s2"), propagation_delay_ms=2.5, capacity=100.0, link_type="isl")
    g.add_edge(NodeId("sat_p0_s2"), NodeId("pod_2"), propagation_delay_ms=2.5, capacity=10.0, link_type="pod")

    return g, registry


class TestPhysicsComputeSynergyRouter:
    def test_instantiation_defaults(self):
        router = PhysicsComputeSynergyRouter()
        assert router._w_delay == 1.0
        assert router._w_queue == 40.0
        assert router._w_compute == 35.0
        assert router._w_thermal == 30.0

    def test_routes_to_lower_delay_when_idle(self):
        g, reg = _build_synergy_graph()
        g.add_edge(NodeId("pod_1"), NodeId("dst"), propagation_delay_ms=1.0, capacity=100.0)
        g.add_edge(NodeId("pod_2"), NodeId("dst"), propagation_delay_ms=1.0, capacity=100.0)
        reg[NodeId("dst")] = RelayNode(NodeId("dst"))
        g.add_node(NodeId("dst"), node_type="sat")

        router = PhysicsComputeSynergyRouter()
        pkt = _make_packet("src", "dst")
        # Path 1 has total delay 5ms vs Path 2 (6ms)
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop == NodeId("sat_p0_s1")

    def test_diverts_away_from_congested_queue(self):
        g, reg = _build_synergy_graph()
        g.add_edge(NodeId("pod_1"), NodeId("dst"), propagation_delay_ms=1.0, capacity=100.0)
        g.add_edge(NodeId("pod_2"), NodeId("dst"), propagation_delay_ms=1.0, capacity=100.0)
        reg[NodeId("dst")] = RelayNode(NodeId("dst"))
        g.add_node(NodeId("dst"), node_type="sat")

        # Fill queue on sat_p0_s1
        sat1 = reg[NodeId("sat_p0_s1")]
        for i in range(80):
            sat1.process_packet(_make_packet("s", "d"))

        router = PhysicsComputeSynergyRouter()
        pkt = _make_packet("src", "dst")
        # Senses queue congestion on sat_p0_s1 and diverts to sat_p0_s2
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop == NodeId("sat_p0_s2")

    def test_diverts_away_from_throttled_compute_pod(self):
        g, reg = _build_synergy_graph()
        # Degrade pod_1 by heating it to 370 K (severe thermal throttling of FLOPS)
        pod1 = reg[NodeId("pod_1")]
        pod1.update_physics({"temperature_k": 370.0})
        
        # Route packet destined for pod_1 vs pod_2
        router = PhysicsComputeSynergyRouter({"w_compute": 50.0})
        pkt = _make_packet("src", "pod_1")
        # Path directly to pod_1
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop == NodeId("sat_p0_s1")

    def test_returns_none_at_destination(self):
        g, reg = _build_synergy_graph()
        router = PhysicsComputeSynergyRouter()
        pkt = _make_packet("src", "src")
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop is None
