"""
Worked example: extending the Layer 3 metrics layer WITHOUT modifying
`skynetra/orchestration/metrics/registry.py`.

Tracks federated-learning round completion. `attach()` subscribes to
`PacketDeliveredEvent`, filtered by `packet_type` — the canonical FL
gradient traffic in this codebase is the `fl_gather` packet type
(`FederatedLearningWorkload` emits gather/broadcast packets; there is
no `fl_gradient` type), configurable via `gradient_packet_type`.

Summary: `rounds_completed`, `mean_round_time_s`, `aggregation_latency_ms`,
`stragglers_per_round`.

Composed the recommended way — no registry mutation:

    sim = OrbitDCSimulation.from_layers(
        ...,
        metrics_collectors=[FLMetricsCollector({"gradient_packet_type": "fl_gather"})],
        ...)

Config keys: `gradient_packet_type` (default "fl_gather"),
`straggler_latency_s` (default 10.0 — a gradient delivery taking longer
than this counts as a straggler).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.events import PacketDeliveredEvent
from skynetra.orchestration.metrics.interface import MetricsCollector

if TYPE_CHECKING:
    import pandas as pd


class FLMetricsCollector(MetricsCollector):
    """Tracks federated-learning round completion via delivered
    gradient packets."""

    name = "fl_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._gradient_packet_type = self._config.get("gradient_packet_type", "fl_gather")
        self._straggler_latency_s = float(self._config.get("straggler_latency_s", 10.0))
        self._round_latencies_s: list[float] = []
        self._stragglers = 0
        self._last_delivery_time: float | None = None
        self._delivery_gaps_ms: list[float] = []

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(PacketDeliveredEvent, self._on_delivered)

    def _on_delivered(self, event: PacketDeliveredEvent) -> None:
        if event.packet.packet_type != self._gradient_packet_type:
            return
        latency_s = event.time - event.packet.created_at
        self._round_latencies_s.append(latency_s)
        if latency_s > self._straggler_latency_s:
            self._stragglers += 1
        if self._last_delivery_time is not None:
            self._delivery_gaps_ms.append((event.time - self._last_delivery_time) * 1000.0)
        self._last_delivery_time = event.time

    def get_summary(self) -> dict[str, Any]:
        rounds = len(self._round_latencies_s)
        mean_round_time_s = sum(self._round_latencies_s) / rounds if rounds else 0.0
        aggregation_latency_ms = (
            sum(self._delivery_gaps_ms) / len(self._delivery_gaps_ms)
            if self._delivery_gaps_ms
            else 0.0
        )
        return {
            "rounds_completed": rounds,
            "mean_round_time_s": mean_round_time_s,
            "aggregation_latency_ms": aggregation_latency_ms,
            "stragglers_per_round": (self._stragglers / rounds) if rounds else 0.0,
        }

    def to_dataframe(self) -> "pd.DataFrame":
        import pandas as pd

        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._round_latencies_s = []
        self._stragglers = 0
        self._last_delivery_time = None
        self._delivery_gaps_ms = []
