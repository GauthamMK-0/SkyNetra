from __future__ import annotations

from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.foundation.types import NodeId
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector


class TestComputeMetricsCollector:
    def test_name(self):
        collector = ComputeMetricsCollector()
        assert collector.name() == "compute"

    def test_collect_empty_context(self):
        collector = ComputeMetricsCollector()
        ctx = SimulationContext()
        metrics = collector.collect(ctx)
        assert metrics["total_compute_tasks"] == 0
        assert metrics["total_compute_flops"] == 0.0
        assert metrics["num_nodes"] == 0

    def test_collect_with_nodes(self):
        collector = ComputeMetricsCollector()
        pod = PodNode(NodeId("pod-1"))
        pod.metrics.compute_tasks = 10
        pod.metrics.compute_flops = 5e12

        relay = RelayNode(NodeId("relay-1"))
        relay.metrics.compute_tasks = 3
        relay.metrics.compute_flops = 1e11

        ctx = SimulationContext(
            nodes={NodeId("pod-1"): pod, NodeId("relay-1"): relay},
        )
        metrics = collector.collect(ctx)
        assert metrics["total_compute_tasks"] == 13
        assert metrics["total_compute_flops"] == 5.1e12
        assert metrics["num_nodes"] == 2

    def test_collect_single_node(self):
        collector = ComputeMetricsCollector()
        pod = PodNode(NodeId("pod-1"))
        pod.metrics.compute_tasks = 7
        pod.metrics.compute_flops = 3e12

        ctx = SimulationContext(nodes={NodeId("pod-1"): pod})
        metrics = collector.collect(ctx)
        assert metrics["total_compute_tasks"] == 7
        assert metrics["total_compute_flops"] == 3e12
        assert metrics["num_nodes"] == 1

    def test_is_metrics_collector(self):
        from skynetra.orchestration.metrics.interface import MetricsCollector
        assert isinstance(ComputeMetricsCollector(), MetricsCollector)

    def test_registered(self):
        from skynetra.orchestration.metrics.registry import STRATEGIES
        assert "compute" in STRATEGIES
        assert STRATEGIES["compute"] is ComputeMetricsCollector
