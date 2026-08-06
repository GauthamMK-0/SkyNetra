"""
Orchestration layer (L3) — compute metrics collector.

Event-driven: subscribes to `ComputeJobCompleteEvent` (finished on-orbit
compute jobs) and `PacketDropEvent` (dropped compute-bound packets:
`flops_required > 0` or a compute workload packet type).

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.events import (
    ComputeJobCompleteEvent,
    PacketDropEvent,
)
from skynetra.orchestration.metrics.interface import MetricsCollector

COMPUTE_PACKET_TYPES = {
    "ai_training_sync",
    "inference_query",
    "fl_gather",
    "fl_broadcast",
}


def _is_compute_packet(packet: Packet) -> bool:
    return packet.flops_required > 0 or packet.packet_type in COMPUTE_PACKET_TYPES


class ComputeMetricsCollector(MetricsCollector):
    """Compute job completion and drop tallies from live events."""

    name: str = "compute_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._jobs_completed = 0
        self._flops_completed = 0.0
        self._compute_drops = 0
        self._jobs_by_pod: dict[str, int] = {}
        self._latency_sum_s = 0.0
        self._latency_count = 0

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(ComputeJobCompleteEvent, self._on_job_complete)
        event_bus.subscribe(PacketDropEvent, self._on_drop)

    def _on_job_complete(self, event: ComputeJobCompleteEvent) -> None:
        self._jobs_completed += 1
        self._flops_completed += float(event.packet.flops_required)
        self._latency_sum_s += float(event.compute_latency_s)
        self._latency_count += 1
        pod_id = str(event.node_id)
        self._jobs_by_pod[pod_id] = self._jobs_by_pod.get(pod_id, 0) + 1

    def _on_drop(self, event: PacketDropEvent) -> None:
        if _is_compute_packet(event.packet):
            self._compute_drops += 1

    def get_summary(self) -> dict[str, Any]:
        return {
            "compute_jobs_completed": self._jobs_completed,
            "compute_flops_completed": self._flops_completed,
            "compute_drops": self._compute_drops,
            "jobs_by_pod": dict(self._jobs_by_pod),
            "avg_compute_latency_s": (
                self._latency_sum_s / self._latency_count if self._latency_count else 0.0
            ),
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._jobs_completed = 0
        self._flops_completed = 0.0
        self._compute_drops = 0
        self._jobs_by_pod = {}
        self._latency_sum_s = 0.0
        self._latency_count = 0
