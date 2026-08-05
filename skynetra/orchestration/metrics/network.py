"""
Orchestration layer (L3) — network metrics collector.

Tallies delivered/dropped packets by subscribing to the typed L3 events
on the event bus (the engine calls `attach` when present — it is not
part of the ABC), and complements the tallies with the cumulative
send/receive counters in each node's `metrics_state`.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.events import PacketDeliveredEvent, PacketDropEvent
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class NetworkMetricsCollector(MetricsCollector):
    def __init__(self) -> None:
        self._delivered = 0
        self._dropped = 0
        self._latency_sum_s = 0.0
        self._latency_count = 0

    def attach(self, event_bus: EventBus) -> None:
        """Subscribe to the packet lifecycle events tallied by `collect`."""
        event_bus.subscribe(PacketDeliveredEvent, self._on_delivered)
        event_bus.subscribe(PacketDropEvent, self._on_dropped)

    def _on_delivered(self, event: PacketDeliveredEvent) -> None:
        self._delivered += 1
        self._latency_sum_s += event.latency_s
        self._latency_count += 1

    def _on_dropped(self, event: PacketDropEvent) -> None:
        self._dropped += 1

    def collect(self, context: SimulationContext) -> dict[str, Any]:
        total_packets = sum(
            node.metrics_state["packets_sent"] + node.metrics_state["packets_received"]
            for node in context.node_registry.values()
        )
        return {
            "total_packets": total_packets,
            "delivered": self._delivered,
            "dropped": self._dropped,
            "avg_latency_s": (
                self._latency_sum_s / self._latency_count if self._latency_count else 0.0
            ),
        }

    def name(self) -> str:
        return "network"


STRATEGIES["network"] = NetworkMetricsCollector
