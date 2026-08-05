from __future__ import annotations

import simpy

from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector


def _compute_packet(packet_id: str, flops: float = 1000.0) -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("sat-1"),
        dst=NodeId("pod-1"),
        size_bytes=200,
        packet_type="compute",
        created_at=0.0,
        flops_required=flops,
    )


def _context(nodes: dict[NodeId, object]) -> SimulationContext:
    return SimulationContext(
        env=simpy.Environment(),
        node_registry=nodes,  # type: ignore[arg-type]
        pod_ids=[nid for nid, node in nodes.items() if node.node_type == "pod"],
    )


class TestComputeMetricsCollector:
    def test_name(self):
        assert ComputeMetricsCollector().name() == "compute"

    def test_counts_pod_compute_activity(self):
        pod = PodNode(NodeId("pod-1"))
        pod.process_packet(_compute_packet("p1"))
        pod.process_compute()
        pod.process_packet(_compute_packet("p2", flops=500.0))
        pod.process_compute()

        metrics = ComputeMetricsCollector().collect(_context({NodeId("pod-1"): pod}))
        assert metrics["total_compute_tasks"] == 2
        assert metrics["total_compute_flops"] == 1500.0
        assert metrics["total_energy_consumed"] == pod.metrics_state["energy_consumed"]
        assert metrics["num_pods"] == 1

    def test_ignores_non_pod_nodes(self):
        relay = RelayNode(NodeId("sat-1"))
        metrics = ComputeMetricsCollector().collect(_context({NodeId("sat-1"): relay}))
        assert metrics["total_compute_tasks"] == 0
        assert metrics["total_compute_flops"] == 0.0
        assert metrics["num_pods"] == 0

    def test_empty_registry(self):
        metrics = ComputeMetricsCollector().collect(_context({}))
        assert metrics["total_compute_tasks"] == 0
        assert metrics["total_compute_flops"] == 0.0
        assert metrics["num_pods"] == 0
