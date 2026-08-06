from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES, get_routing_engine
from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.foundation.errors import RoutingError
from skynetra.foundation.types import LinkId, NodeId


def _graph() -> nx.DiGraph:
    """Two competing paths s->t: fast a-path (2 ms) and slow b-path (6 ms)."""
    g = nx.DiGraph()
    for nid in ("s", "a", "b", "t"):
        g.add_node(nid, node_type="sat")
    g.add_edge("s", "a", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("a", "t", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("s", "b", propagation_delay_ms=3.0, capacity=10.0)
    g.add_edge("b", "t", propagation_delay_ms=3.0, capacity=10.0)
    return g


def _node_registry() -> dict[NodeId, Node]:
    return {NodeId(nid): RelayNode(NodeId(nid)) for nid in ("s", "a", "b", "t")}


def _packet() -> Packet:
    return Packet(
        packet_id="pkt-1",
        src=NodeId("s"),
        dst=NodeId("t"),
        size_bytes=100,
        packet_type="data",
        created_at=0.0,
    )


class TestShortestPathRouterDelay:
    def test_router_is_routing_engine(self):
        assert isinstance(ShortestPathRouter(), RoutingEngine)

    def test_correct_next_hop(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry())
            == NodeId("a")
        )

    def test_next_hop_along_route(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        packet = _packet()
        assert router.select_next_hop(packet, NodeId("s"), graph, _node_registry()) == NodeId("a")
        assert router.select_next_hop(packet, NodeId("a"), graph, _node_registry()) == NodeId("t")

    def test_direct_edge_to_destination(self):
        graph = nx.DiGraph()
        graph.add_node("s", node_type="sat")
        graph.add_node("t", node_type="sat")
        graph.add_edge("s", "t", propagation_delay_ms=5.0, capacity=10.0)
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry())
            == NodeId("t")
        )

    def test_at_destination_returns_none(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("t"), graph, _node_registry())
            is None
        )

    def test_no_path_returns_none(self):
        graph = nx.DiGraph()
        graph.add_node("s", node_type="sat")
        graph.add_node("t", node_type="sat")
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry()) is None

    def test_update_topology_refreshes_tables(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry())
            == NodeId("a")
        )
        graph.edges["s", "a"]["propagation_delay_ms"] = 1000.0
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry())
            == NodeId("b")
        )


class TestShortestPathRouterWeightModes:
    def test_hops_mode_prefers_fewer_hops(self):
        graph = nx.DiGraph()
        for nid in ("s", "a", "t"):
            graph.add_node(nid, node_type="sat")
        graph.add_edge("s", "a", propagation_delay_ms=1.0, capacity=10.0)
        graph.add_edge("a", "t", propagation_delay_ms=1.0, capacity=10.0)
        graph.add_edge("s", "t", propagation_delay_ms=1000.0, capacity=10.0)
        registry = _node_registry()
        router = ShortestPathRouter({"weight_mode": "hops"})
        router.update_topology(graph)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("t")

    def test_delay_mode_prefers_low_delay(self):
        graph = nx.DiGraph()
        for nid in ("s", "a", "t"):
            graph.add_node(nid, node_type="sat")
        graph.add_edge("s", "a", propagation_delay_ms=1.0, capacity=10.0)
        graph.add_edge("a", "t", propagation_delay_ms=1.0, capacity=10.0)
        graph.add_edge("s", "t", propagation_delay_ms=1000.0, capacity=10.0)
        registry = _node_registry()
        router = ShortestPathRouter({"weight_mode": "delay"})
        router.update_topology(graph)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("a")

    def test_capacity_mode_prefers_high_capacity(self):
        graph = nx.DiGraph()
        for nid in ("s", "a", "b", "t"):
            graph.add_node(nid, node_type="sat")
        graph.add_edge("s", "a", propagation_delay_ms=1.0, capacity=1.0)
        graph.add_edge("a", "t", propagation_delay_ms=1.0, capacity=1.0)
        graph.add_edge("s", "b", propagation_delay_ms=1.0, capacity=100.0)
        graph.add_edge("b", "t", propagation_delay_ms=1.0, capacity=100.0)
        registry = _node_registry()
        router = ShortestPathRouter({"weight_mode": "capacity"})
        router.update_topology(graph)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("b")

    def test_unknown_weight_mode_raises(self):
        with pytest.raises(ValueError):
            ShortestPathRouter({"weight_mode": "magic"})

    def test_default_mode_is_delay(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry())
            == NodeId("a")
        )


class TestShortestPathRouterOperationalFilter:
    def test_excludes_non_operational_nodes(self):
        graph = _graph()
        registry = _node_registry()
        registry[NodeId("a")].update_physics({"fault_probability": 0.9})
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("b")

    def test_source_faulted_returns_none(self):
        graph = _graph()
        registry = _node_registry()
        registry[NodeId("s")].update_physics({"fault_probability": 0.9})
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) is None

    def test_filter_operational_nodes(self):
        graph = _graph()
        registry = _node_registry()
        registry[NodeId("a")].update_physics({"fault_probability": 0.9})
        router = ShortestPathRouter()
        filtered = router.filter_operational_nodes(graph, registry)
        assert NodeId("a") not in filtered
        assert NodeId("s") in filtered


class TestShortestPathRouterWeightOverrides:
    def test_positive_override_forces_avoidance(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        overrides = {LinkId("s->a"): 999.0}
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry(), overrides)
            == NodeId("b")
        )

    def test_none_overrides_use_tables(self):
        graph = _graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, _node_registry(), None)
            == NodeId("a")
        )

    def test_get_edge_weight_base_and_override(self):
        graph = _graph()
        router = ShortestPathRouter()
        registry = _node_registry()
        assert (
            router.get_edge_weight(graph, NodeId("s"), NodeId("a"), registry)
            == pytest.approx(1.0)
        )
        overrides = {LinkId("s->a"): 4.5}
        assert (
            router.get_edge_weight(graph, NodeId("s"), NodeId("a"), registry, overrides)
            == pytest.approx(5.5)
        )


class TestRoutingRegistry:
    def test_known_names_instantiate(self):
        for name, expected in STRATEGIES.items():
            engine = get_routing_engine(name)
            assert isinstance(engine, RoutingEngine)
            assert isinstance(engine, expected)

    def test_known_name_with_config(self):
        engine = get_routing_engine("shortest_path", {"weight_mode": "hops"})
        assert engine._config["weight_mode"] == "hops"

    def test_unknown_name_raises_routing_error(self):
        with pytest.raises(RoutingError) as excinfo:
            get_routing_engine("bogus_router")
        message = str(excinfo.value)
        assert "Unknown routing strategy 'bogus_router'" in message
        assert "'shortest_path'" in message
        assert "'backpressure'" in message

    def test_static_strategy_set(self):
        assert set(STRATEGIES.keys()) == {"shortest_path", "backpressure"}


def _pod_transit_graph() -> nx.DiGraph:
    """Shortest s->t path cuts THROUGH pod p (3 hops via p vs 4 via sats)."""
    g = nx.DiGraph()
    for nid, ntype in (("s", "sat"), ("p", "pod"), ("a", "sat"), ("b", "sat"), ("t", "sat")):
        g.add_node(nid, node_type=ntype)
    g.add_edge("s", "p", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("p", "a", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("a", "t", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("s", "b", propagation_delay_ms=2.0, capacity=10.0)
    g.add_edge("b", "t", propagation_delay_ms=2.0, capacity=10.0)
    return g


class TestShortestPathNeverTransitsPods:
    def test_precomputed_route_skips_pod(self):
        graph = _pod_transit_graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        registry = {NodeId(nid): RelayNode(NodeId(nid)) for nid in ("s", "a", "b", "t")}
        hop = router.select_next_hop(_packet(), NodeId("s"), graph, registry)
        assert hop == NodeId("b")

    def test_live_dijkstra_route_to_pod_destination(self):
        graph = _pod_transit_graph()
        router = ShortestPathRouter()
        router.update_topology(graph)
        packet = _packet()
        packet.dst = NodeId("p")
        registry = {NodeId(nid): RelayNode(NodeId(nid)) for nid in ("s", "a", "b", "t")}
        assert router.select_next_hop(packet, NodeId("s"), graph, registry) == NodeId("p")
