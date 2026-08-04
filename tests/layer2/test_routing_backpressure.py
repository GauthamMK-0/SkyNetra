from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.backpressure import BackPressureConfig, BackPressureRouter
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId


def _graph() -> nx.DiGraph:
    """Two paths s->t: a-path (2 ms total) and slightly slower b-path (6 ms)."""
    g = nx.DiGraph()
    for nid in ("s", "a", "b", "t"):
        g.add_node(nid, node_type="sat")
    g.add_edge("s", "a", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("a", "t", propagation_delay_ms=1.0, capacity=10.0)
    g.add_edge("s", "b", propagation_delay_ms=3.0, capacity=10.0)
    g.add_edge("b", "t", propagation_delay_ms=3.0, capacity=10.0)
    return g


def _registry_with_queue_at_a(queue_depth: int = 50) -> dict[NodeId, Node]:
    registry = {
        NodeId(nid): RelayNode(NodeId(nid)) for nid in ("s", "a", "b", "t")
    }
    for i in range(queue_depth):
        registry[NodeId("a")].process_packet(
            Packet(f"q-{i}", NodeId("s"), NodeId("t"), 100, "data", 0.0)
        )
    return registry


def _packet() -> Packet:
    return Packet(
        packet_id="pkt-1",
        src=NodeId("s"),
        dst=NodeId("t"),
        size_bytes=100,
        packet_type="data",
        created_at=0.0,
    )


class TestBackPressureConfig:
    def test_defaults(self):
        config = BackPressureConfig()
        assert config.alpha == 1.0
        assert config.beta == 5.0
        assert config.gamma == 50.0
        assert config.delta == 30.0
        assert config.epsilon == 1.0
        assert config.kappa_thermal == 20.0
        assert config.kappa_radiation == 1000.0
        assert config.avoid_faulty_nodes is True

    def test_router_exposes_params(self):
        router = BackPressureRouter()
        assert isinstance(router.params, BackPressureConfig)
        assert router.params == BackPressureConfig()

    def test_dict_config_maps_to_params(self):
        router = BackPressureRouter({"gamma": 0.0, "avoid_faulty_nodes": False})
        assert router.params.gamma == 0.0
        assert router.params.avoid_faulty_nodes is False


class TestBackPressureRouter:
    def test_router_is_routing_engine(self):
        assert isinstance(BackPressureRouter(), RoutingEngine)

    def test_default_chooses_lowest_delay(self):
        graph = _graph()
        router = BackPressureRouter()
        registry = _registry_with_queue_at_a(queue_depth=0)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("a")

    def test_reroutes_around_high_queue_node(self):
        graph = _graph()
        router = BackPressureRouter()
        registry = _registry_with_queue_at_a(queue_depth=50)
        assert registry[NodeId("a")].get_utilization() == pytest.approx(0.5)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("b")

    def test_gamma_zero_ignores_queue_pressure(self):
        graph = _graph()
        router = BackPressureRouter({"gamma": 0.0})
        registry = _registry_with_queue_at_a(queue_depth=50)
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("a")

    def test_compute_backlog_penalizes_pod(self):
        graph = _graph()
        registry = {NodeId(nid): RelayNode(NodeId(nid)) for nid in ("s", "b", "t")}
        pod = PodNode(NodeId("a"))
        for i in range(5):
            pod.process_packet(
                Packet(f"c-{i}", NodeId("s"), NodeId("a"), 100, "compute", 0.0, flops_required=1e9)
            )
        registry[NodeId("a")] = pod
        router = BackPressureRouter()
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("b")

    def test_at_destination_returns_none(self):
        graph = _graph()
        router = BackPressureRouter()
        assert (
            router.select_next_hop(_packet(), NodeId("t"), graph, _registry_with_queue_at_a())
            is None
        )

    def test_no_candidates_returns_none(self):
        graph = nx.DiGraph()
        graph.add_node("s", node_type="sat")
        graph.add_node("t", node_type="sat")
        graph.add_edge("s", "t", propagation_delay_ms=1.0, capacity=10.0)
        registry = {NodeId("s"): RelayNode(NodeId("s")), NodeId("t"): RelayNode(NodeId("t"))}
        packet = _packet()
        router = BackPressureRouter()
        assert router.select_next_hop(packet, NodeId("t"), graph, registry) is None

    def test_update_topology_is_noop(self):
        router = BackPressureRouter()
        router.update_topology(_graph())
        assert (
            router.select_next_hop(
                _packet(), NodeId("s"), _graph(), _registry_with_queue_at_a(queue_depth=0)
            )
            == NodeId("a")
        )


class TestBackPressurePhysicsPenalty:
    def test_penalty_exactly_zero_when_overrides_none(self):
        router = BackPressureRouter()
        assert router.physics_penalty(NodeId("s"), NodeId("a"), None) == 0.0

    def test_penalty_exactly_zero_when_overrides_empty(self):
        router = BackPressureRouter()
        assert router.physics_penalty(NodeId("s"), NodeId("a"), {}) == 0.0

    def test_penalty_reads_override(self):
        router = BackPressureRouter()
        overrides = {LinkId("s->a"): 42.5}
        assert router.physics_penalty(NodeId("s"), NodeId("a"), overrides) == pytest.approx(42.5)

    def test_penalty_zero_for_unlisted_edge(self):
        router = BackPressureRouter()
        overrides = {LinkId("s->b"): 42.5}
        assert router.physics_penalty(NodeId("s"), NodeId("a"), overrides) == 0.0

    def test_large_override_forces_avoidance(self):
        graph = _graph()
        router = BackPressureRouter()
        registry = _registry_with_queue_at_a(queue_depth=0)
        overrides = {LinkId("s->a"): 999.0}
        assert (
            router.select_next_hop(_packet(), NodeId("s"), graph, registry, overrides)
            == NodeId("b")
        )


class TestBackPressureAvoidFaultyNodes:
    def test_faulted_node_excluded_by_default(self):
        graph = _graph()
        registry = _registry_with_queue_at_a(queue_depth=0)
        registry[NodeId("a")].update_physics({"fault_probability": 0.9})
        router = BackPressureRouter()
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("b")

    def test_faulted_node_allowed_when_disabled(self):
        graph = _graph()
        registry = _registry_with_queue_at_a(queue_depth=0)
        registry[NodeId("a")].update_physics({"fault_probability": 0.9})
        router = BackPressureRouter({"avoid_faulty_nodes": False})
        assert router.select_next_hop(_packet(), NodeId("s"), graph, registry) == NodeId("a")
