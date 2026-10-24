"""
Tests for GeographicGreedyRouter (GPSR-Space).
"""

from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.geographic import GeographicGreedyRouter
from skynetra.foundation.types import NodeId


def _make_packet(src: str, dst: str) -> Packet:
    return Packet(
        packet_id="pkt-test",
        src=NodeId(src),
        dst=NodeId(dst),
        size_bytes=1000,
        packet_type="data",
        created_at=0.0,
    )


def _build_test_graph() -> tuple[nx.DiGraph, dict[NodeId, RelayNode]]:
    """Build a linear 3-hop graph with 3D positions:
    n1 (0, 0, 0) -> n2 (1000, 0, 0) -> n3 (2000, 0, 0) -> dst (3000, 0, 0)
    and an alternative branch n1 -> n_alt (0, 2000, 0).
    """
    g = nx.DiGraph()
    positions = {
        "n1": (0.0, 0.0, 0.0),
        "n2": (1000.0, 0.0, 0.0),
        "n3": (2000.0, 0.0, 0.0),
        "dst": (3000.0, 0.0, 0.0),
        "n_alt": (0.0, 2000.0, 0.0),
    }
    registry: dict[NodeId, RelayNode] = {}
    for nid, pos in positions.items():
        g.add_node(NodeId(nid), position=pos, node_type="sat")
        registry[NodeId(nid)] = RelayNode(NodeId(nid))

    g.add_edge(NodeId("n1"), NodeId("n2"), propagation_delay_ms=3.3, capacity=100.0)
    g.add_edge(NodeId("n1"), NodeId("n_alt"), propagation_delay_ms=6.6, capacity=100.0)
    g.add_edge(NodeId("n2"), NodeId("n3"), propagation_delay_ms=3.3, capacity=100.0)
    g.add_edge(NodeId("n3"), NodeId("dst"), propagation_delay_ms=3.3, capacity=100.0)

    return g, registry


class TestGeographicGreedyRouter:
    def test_instantiation_defaults(self):
        router = GeographicGreedyRouter()
        assert router._fallback_to_min_delay is True
        assert router._avoid_faulty_nodes is True

    def test_select_destination_when_adjacent(self):
        g, reg = _build_test_graph()
        router = GeographicGreedyRouter()
        pkt = _make_packet("n3", "dst")
        next_hop = router.select_next_hop(pkt, NodeId("n3"), g, reg)
        assert next_hop == NodeId("dst")

    def test_greedy_progression_toward_target(self):
        g, reg = _build_test_graph()
        router = GeographicGreedyRouter()
        pkt = _make_packet("n1", "dst")
        # n2 is at dist 2000 to dst; n_alt is at dist sqrt(3000^2 + 2000^2) = 3605
        next_hop = router.select_next_hop(pkt, NodeId("n1"), g, reg)
        assert next_hop == NodeId("n2")

    def test_return_none_at_destination(self):
        g, reg = _build_test_graph()
        router = GeographicGreedyRouter()
        pkt = _make_packet("n1", "dst")
        next_hop = router.select_next_hop(pkt, NodeId("dst"), g, reg)
        assert next_hop is None

    def test_local_minimum_fallback_to_min_delay(self):
        """When candidates are farther than current node, fallback to lowest delay."""
        g = nx.DiGraph()
        g.add_node(NodeId("curr"), position=(1000.0, 0.0, 0.0), node_type="sat")
        g.add_node(NodeId("nbr1"), position=(2000.0, 1000.0, 0.0), node_type="sat")
        g.add_node(NodeId("nbr2"), position=(2000.0, 2000.0, 0.0), node_type="sat")
        g.add_node(NodeId("target"), position=(0.0, 0.0, 0.0), node_type="sat")

        # curr is at dist 1000 to target; nbr1 is at dist ~2236, nbr2 is at dist ~2828
        g.add_edge(NodeId("curr"), NodeId("nbr1"), propagation_delay_ms=2.0, capacity=10.0)
        g.add_edge(NodeId("curr"), NodeId("nbr2"), propagation_delay_ms=8.0, capacity=10.0)

        reg = {
            NodeId("curr"): RelayNode(NodeId("curr")),
            NodeId("nbr1"): RelayNode(NodeId("nbr1")),
            NodeId("nbr2"): RelayNode(NodeId("nbr2")),
            NodeId("target"): RelayNode(NodeId("target")),
        }

        router = GeographicGreedyRouter({"fallback_to_min_delay": True})
        pkt = _make_packet("curr", "target")
        next_hop = router.select_next_hop(pkt, NodeId("curr"), g, reg)
        assert next_hop == NodeId("nbr1")

    def test_avoid_faulty_nodes(self):
        g, reg = _build_test_graph()
        # Fault n2 (temperature > fault threshold 400 K)
        reg[NodeId("n2")].update_physics({"temperature_k": 450.0})
        assert not reg[NodeId("n2")].is_operational()

        router = GeographicGreedyRouter()
        pkt = _make_packet("n1", "dst")
        # Should divert to n_alt since n2 is faulty
        next_hop = router.select_next_hop(pkt, NodeId("n1"), g, reg)
        assert next_hop == NodeId("n_alt")
