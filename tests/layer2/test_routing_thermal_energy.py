"""
Tests for ThermalEnergyAwareRouter (TEHR).
"""

from __future__ import annotations

import networkx as nx

from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.thermal_energy import ThermalEnergyAwareRouter
from skynetra.foundation.types import NodeId


def _make_packet(src: str, dst: str) -> Packet:
    return Packet(
        packet_id="pkt-tehr",
        src=NodeId(src),
        dst=NodeId(dst),
        size_bytes=1000,
        packet_type="data",
        created_at=0.0,
    )


def _build_diamond_graph() -> tuple[nx.DiGraph, dict[NodeId, RelayNode]]:
    """Diamond graph:
    src -> hot_node -> dst  (delay: 5ms)
    src -> cool_node -> dst (delay: 7ms)
    """
    g = nx.DiGraph()
    registry: dict[NodeId, RelayNode] = {}
    for nid in ("src", "hot_node", "cool_node", "dst"):
        g.add_node(NodeId(nid), node_type="sat")
        registry[NodeId(nid)] = RelayNode(NodeId(nid))

    g.add_edge(NodeId("src"), NodeId("hot_node"), propagation_delay_ms=2.5, capacity=100.0)
    g.add_edge(NodeId("hot_node"), NodeId("dst"), propagation_delay_ms=2.5, capacity=100.0)
    g.add_edge(NodeId("src"), NodeId("cool_node"), propagation_delay_ms=3.5, capacity=100.0)
    g.add_edge(NodeId("cool_node"), NodeId("dst"), propagation_delay_ms=3.5, capacity=100.0)

    return g, registry


class TestThermalEnergyAwareRouter:
    def test_instantiation_defaults(self):
        router = ThermalEnergyAwareRouter()
        assert router._alpha_delay == 1.0
        assert router._beta_thermal == 15.0
        assert router._gamma_energy == 25.0

    def test_prefers_lower_delay_when_nominal(self):
        g, reg = _build_diamond_graph()
        router = ThermalEnergyAwareRouter()
        pkt = _make_packet("src", "dst")
        # Both paths nominal -> lower delay path (hot_node, 5ms total vs 7ms) wins
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop == NodeId("hot_node")

    def test_diverts_away_from_overheated_satellite(self):
        g, reg = _build_diamond_graph()
        # Heat hot_node up to 365 K (near critical threshold)
        reg[NodeId("hot_node")].update_physics({"temperature_k": 365.0})
        reg[NodeId("cool_node")].update_physics({"temperature_k": 295.0})

        router = ThermalEnergyAwareRouter({"beta_thermal": 50.0})
        pkt = _make_packet("src", "dst")
        # Thermal penalty should make cool_node cheaper
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop == NodeId("cool_node")

    def test_diverts_away_from_depleted_battery_node(self):
        g, reg = _build_diamond_graph()
        # Drain power on hot_node (e.g. deep eclipse: 40 W vs nominal 1000 W)
        reg[NodeId("hot_node")].update_physics({"power_available_w": 40.0})
        reg[NodeId("cool_node")].update_physics({"power_available_w": 1000.0})

        router = ThermalEnergyAwareRouter({"gamma_energy": 50.0})
        pkt = _make_packet("src", "dst")
        next_hop = router.select_next_hop(pkt, NodeId("src"), g, reg)
        assert next_hop == NodeId("cool_node")

    def test_direct_adjacent_destination(self):
        g, reg = _build_diamond_graph()
        router = ThermalEnergyAwareRouter()
        pkt = _make_packet("hot_node", "dst")
        next_hop = router.select_next_hop(pkt, NodeId("hot_node"), g, reg)
        assert next_hop == NodeId("dst")

    def test_returns_none_at_destination(self):
        g, reg = _build_diamond_graph()
        router = ThermalEnergyAwareRouter()
        pkt = _make_packet("src", "dst")
        next_hop = router.select_next_hop(pkt, NodeId("dst"), g, reg)
        assert next_hop is None
