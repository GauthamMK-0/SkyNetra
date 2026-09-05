"""
Orchestration layer (L3) — physics metrics collector.

Event-driven: subscribes to `PhysicsTickEvent` (per-node physics state
after each tick) and `PacketDropEvent`, filtered to physics-caused drops
(`PhysicsInducedDropEvent` instances).

From each tick's node state it counts deterministic state-derived
events:

  * `thermal_throttle_events`: nodes running above nominal temperature
    (>= TEMP_NOMINAL_K + TEMP_DEGRADATION_SIGMA_K) but below the thermal
    fault threshold — throttling, not faulted.
  * `radiation_fault_events`: nodes faulted by latch-up
    (fault_probability >= FAULT_PROBABILITY_THRESHOLD) while below the
    thermal fault threshold — the fault is radiation-induced.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from skynetra.domain.nodes.base import (
    FAULT_PROBABILITY_THRESHOLD,
    TEMP_DEGRADATION_SIGMA_K,
    TEMP_FAULT_THRESHOLD_K,
    TEMP_NOMINAL_K,
)
from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.events import (
    PacketDropEvent,
    PhysicsInducedDropEvent,
    PhysicsTickEvent,
)
from skynetra.orchestration.metrics.interface import MetricsCollector

THERMAL_THROTTLE_THRESHOLD_K = TEMP_NOMINAL_K + TEMP_DEGRADATION_SIGMA_K


class PhysicsMetricsCollector(MetricsCollector):
    """Physics-state event counters from live physics ticks and drops."""

    name: str = "physics_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._thermal_throttle_events = 0
        self._radiation_fault_events = 0
        self._physics_caused_drops = 0
        self._temperature_sum = 0.0
        self._temperature_count = 0
        self._last_energy: dict[str, float] = {}
        self._active_models: list[str] = []

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(PhysicsTickEvent, self._on_physics_tick)
        event_bus.subscribe(PacketDropEvent, self._on_drop)

    def _on_physics_tick(self, event: PhysicsTickEvent) -> None:
        self._active_models = list(event.active_models)
        for node_id, state in event.node_state.items():
            physics_state = state.get("physics_state", state)
            temperature_k = float(physics_state["temperature_k"])
            fault_probability = float(physics_state["fault_probability"])

            throttling = (
                THERMAL_THROTTLE_THRESHOLD_K <= temperature_k < TEMP_FAULT_THRESHOLD_K
            )
            radiation_faulted = (
                fault_probability >= FAULT_PROBABILITY_THRESHOLD
                and temperature_k < TEMP_FAULT_THRESHOLD_K
            )
            if throttling:
                self._thermal_throttle_events += 1
            if radiation_faulted:
                self._radiation_fault_events += 1

            self._temperature_sum += temperature_k
            self._temperature_count += 1
            metrics_state = state.get("metrics_state")
            if metrics_state is not None:
                self._last_energy[node_id] = float(metrics_state["energy_consumed"])

    def _on_drop(self, event: PacketDropEvent) -> None:
        if isinstance(event, PhysicsInducedDropEvent):
            self._physics_caused_drops += 1

    def get_summary(self) -> dict[str, Any]:
        return {
            "thermal_throttle_events": self._thermal_throttle_events,
            "radiation_fault_events": self._radiation_fault_events,
            "physics_caused_drops": self._physics_caused_drops,
            "avg_temperature": (
                self._temperature_sum / self._temperature_count if self._temperature_count else 0.0
            ),
            "total_energy_consumed": sum(self._last_energy.values()),
            "active_models": list(self._active_models),
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._thermal_throttle_events = 0
        self._radiation_fault_events = 0
        self._physics_caused_drops = 0
        self._temperature_sum = 0.0
        self._temperature_count = 0
        self._last_energy = {}
        self._active_models = []
