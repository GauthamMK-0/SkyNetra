"""
L3 tests — pod compute service time (Phase 2).

The engine's per-pod `_compute_loop` serves tasks with
`service_s = flops_required / available_compute_flops()`; end-to-end
compute latency (ComputeJobCompleteEvent.compute_latency_s) must scale
with flops and with thermal degradation.

Topology: same deterministic 1x2 constellation as test_link_dynamics —
gs-1 -> sat-0-0 -> pod-1 forced path; transit time is ~3.7 ms (two
550 km hops, tiny packets).
"""

from __future__ import annotations

from typing import Any

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import ReferenceCircularPropagator
from skynetra.engines.routing.registry import get_routing_engine
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import ComputeJobCompleteEvent
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector

CONSTELLATION_1X2 = ConstellationConfig(
    n_planes=1, sats_per_plane=2, altitude_km=550, inclination_deg=55
)

GS_1 = NodeId("gs-1")
POD_1 = NodeId("pod-1")


class SingleTaskWorkload(WorkloadGenerator):
    """Emits one compute task gs-1 -> pod-1 with the given flops."""

    def __init__(self, flops_required: float) -> None:
        super().__init__()
        self._flops_required = flops_required

    def generate(
        self,
        env: Any,
        publish_packet: Any,
        node_registry: dict[NodeId, Node],
    ) -> Any:
        publish_packet(
            self.create_packet(
                env,
                GS_1,
                POD_1,
                size_bytes=256,
                packet_type="inference_query",
                flops_required=self._flops_required,
            )
        )
        yield env.timeout(0.0)


def _registry(pod_flops: float = 1e12, temperature_k: float = 293.15) -> dict[NodeId, Node]:
    propagator = ReferenceCircularPropagator()
    registry: dict[NodeId, Node] = {
        sat_id: RelayNode(sat_id) for sat_id in propagator.get_sat_ids(CONSTELLATION_1X2)
    }
    pod = PodNode(POD_1, flops=pod_flops)
    if temperature_k != 293.15:
        pod.update_physics({"temperature_k": temperature_k})
    registry[POD_1] = pod
    registry[GS_1] = GroundStationNode(GS_1)
    return registry


def _sim(
    flops_required: float,
    pod_flops: float = 1e12,
    temperature_k: float = 293.15,
) -> OrbitDCSimulation:
    return OrbitDCSimulation.from_layers(
        constellation=CONSTELLATION_1X2,
        node_registry=_registry(pod_flops=pod_flops, temperature_k=temperature_k),
        routing_engine=get_routing_engine("shortest_path"),
        workloads=[SingleTaskWorkload(flops_required)],
        metrics_collectors=[ComputeMetricsCollector()],
        topology_update_interval_s=1000.0,
        sim_duration_s=10.0,
    )


def _latency(sim: OrbitDCSimulation) -> float:
    results = sim.run()
    events = [
        ev
        for ev in results.events
        if isinstance(ev, ComputeJobCompleteEvent) and ev.node_id == POD_1
    ]
    assert len(events) == 1, "expected exactly one completed compute job"
    return events[0].compute_latency_s


class TestComputeService:
    def test_compute_latency_scales_with_flops(self):
        small = _latency(_sim(flops_required=1e12))
        large = _latency(_sim(flops_required=2e12))

        # Same transit path in both runs; the difference is exactly the
        # extra 1 s of service at the 1e12 flops pod rate.
        assert large - small == pytest.approx(1.0, abs=0.02)

    def test_compute_latency_includes_service_time(self):
        # service 1 s + ~3.7 ms transit.
        assert _latency(_sim(flops_required=1e12)) == pytest.approx(1.004, abs=0.02)

    def test_thermal_degradation_slows_compute(self):
        # available = 1e12 * exp(-50/50) = 3.679e11 -> service 2.718 s.
        assert _latency(_sim(flops_required=1e12, temperature_k=350.0)) == pytest.approx(
            2.722, abs=0.02
        )

    def test_compute_job_event_and_metrics(self):
        sim = _sim(flops_required=1e12)
        results = sim.run()
        compute_events = [
            ev
            for ev in results.events
            if isinstance(ev, ComputeJobCompleteEvent) and ev.node_id == POD_1
        ]
        assert len(compute_events) == 1
        assert compute_events[0].compute_latency_s > 1.0

        compute_metrics = results.engine_metrics["compute_metrics"]
        assert compute_metrics["compute_jobs_completed"] == 1
        assert compute_metrics["compute_flops_completed"] == 1e12
        assert compute_metrics["avg_compute_latency_s"] > 1.0

    def test_pod_queue_drains_after_service(self):
        sim = _sim(flops_required=1e12)
        sim.run()
        pod = sim.setup().node_registry[POD_1]
        assert pod.get_queue_depth() == 0
        assert pod.metrics_state["compute_tasks"] == 1
        assert pod.metrics_state["compute_flops"] == 1e12
