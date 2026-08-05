"""
Orchestration layer (L3) — network metrics collector.

Event-driven: subscribes to the packet lifecycle events (`PacketDeliveredEvent`,
`PacketDropEvent`, `PacketTransmitEvent`) and tallies delivered/dropped/
transmitted counts plus average end-to-end latency.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.events import (
    PacketDeliveredEvent,
    PacketDropEvent,
    PacketTransmitEvent,
)
from skynetra.orchestration.metrics.interface import MetricsCollector


class NetworkMetricsCollector(MetricsCollector):
    """Delivered/dropped/transmitted packet tallies from live events."""

    name: str = "network_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._delivered = 0
        self._dropped = 0
        self._transmitted = 0
        self._latency_sum_s = 0.0
        self._latency_count = 0

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(PacketDeliveredEvent, self._on_delivered)
        event_bus.subscribe(PacketDropEvent, self._on_dropped)
        event_bus.subscribe(PacketTransmitEvent, self._on_transmitted)

    def _on_delivered(self, event: PacketDeliveredEvent) -> None:
        self._delivered += 1
        self._latency_sum_s += event.latency_s
        self._latency_count += 1

    def _on_dropped(self, event: PacketDropEvent) -> None:
        self._dropped += 1

    def _on_transmitted(self, event: PacketTransmitEvent) -> None:
        self._transmitted += 1

    def get_summary(self) -> dict[str, Any]:
        completed = self._delivered + self._dropped
        return {
            "delivered": self._delivered,
            "dropped": self._dropped,
            "transmitted": self._transmitted,
            "avg_latency_s": (
                self._latency_sum_s / self._latency_count if self._latency_count else 0.0
            ),
            "drop_rate": (self._dropped / completed if completed else 0.0),
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._delivered = 0
        self._dropped = 0
        self._transmitted = 0
        self._latency_sum_s = 0.0
        self._latency_count = 0
