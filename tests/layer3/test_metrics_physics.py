from __future__ import annotations

from skynetra.domain.nodes.base import PhysicsState
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.foundation.types import NodeId
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.physics_metrics import PhysicsMetricsCollector


class TestPhysicsMetricsCollector:
    def test_name(self):
        collector = PhysicsMetricsCollector()
        assert collector.name() == "physics"

    def test_collect_empty_context(self):
        collector = PhysicsMetricsCollector()
        ctx = SimulationContext()
        metrics = collector.collect(ctx)
        assert metrics["total_energy_consumed"] == 0.0
        assert metrics["avg_temperature"] == 0.0
        assert metrics["num_nodes"] == 0

    def test_collect_with_nodes(self):
        collector = PhysicsMetricsCollector()
        node_a = RelayNode(NodeId("a"))
        node_b = RelayNode(NodeId("b"))
        node_a.physics = PhysicsState(temperature=300.0)
        node_b.physics = PhysicsState(temperature=320.0)
        node_a.metrics.energy_consumed = 100.0
        node_b.metrics.energy_consumed = 200.0

        ctx = SimulationContext(
            nodes={NodeId("a"): node_a, NodeId("b"): node_b},
        )
        metrics = collector.collect(ctx)
        assert metrics["total_energy_consumed"] == 300.0
        assert metrics["avg_temperature"] == 310.0
        assert metrics["num_nodes"] == 2

    def test_collect_single_node(self):
        collector = PhysicsMetricsCollector()
        node = PodNode(NodeId("pod-1"))
        node.physics = PhysicsState(temperature=273.15)
        node.metrics.energy_consumed = 50.0

        ctx = SimulationContext(nodes={NodeId("pod-1"): node})
        metrics = collector.collect(ctx)
        assert metrics["total_energy_consumed"] == 50.0
        assert metrics["avg_temperature"] == 273.15
        assert metrics["num_nodes"] == 1

    def test_is_metrics_collector(self):
        from skynetra.orchestration.metrics.interface import MetricsCollector
        assert isinstance(PhysicsMetricsCollector(), MetricsCollector)

    def test_registered(self):
        from skynetra.orchestration.metrics.registry import STRATEGIES
        assert "physics" in STRATEGIES
        assert STRATEGIES["physics"] is PhysicsMetricsCollector
