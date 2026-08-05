"""
Orchestration layer (L3) — physics metrics collector.

Reads each node's `physics_state` (pushed by the Layer 2 physics models)
and counts deterministic state-derived events:

  * `thermal_throttle_events`: nodes running above nominal temperature
    (>= TEMP_NOMINAL_K + TEMP_DEGRADATION_SIGMA_K) but below the fault
    threshold — they are throttling, not faulted.
  * `radiation_fault_events`: nodes faulted by latch-up (fault_probability
    >= FAULT_PROBABILITY_THRESHOLD) while below the thermal fault
    threshold — the fault is radiation-induced.

`active_models` lists the names of the enabled physics models on the
orchestrator, so consumers can see which engines contributed.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.domain.nodes.base import (
    FAULT_PROBABILITY_THRESHOLD,
    TEMP_DEGRADATION_SIGMA_K,
    TEMP_FAULT_THRESHOLD_K,
    TEMP_NOMINAL_K,
)
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES

THERMAL_THROTTLE_THRESHOLD_K = TEMP_NOMINAL_K + TEMP_DEGRADATION_SIGMA_K


class PhysicsMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> dict[str, Any]:
        thermal_throttle_events = 0
        radiation_fault_events = 0
        total_energy = 0.0
        temp_sum = 0.0

        for node in context.node_registry.values():
            state = node.physics_state
            temperature_k = state["temperature_k"]
            total_energy += float(node.metrics_state["energy_consumed"])
            temp_sum += temperature_k

            throttling = (
                THERMAL_THROTTLE_THRESHOLD_K <= temperature_k
                and temperature_k < TEMP_FAULT_THRESHOLD_K
            )
            radiation_faulted = (
                state["fault_probability"] >= FAULT_PROBABILITY_THRESHOLD
                and temperature_k < TEMP_FAULT_THRESHOLD_K
            )
            if throttling:
                thermal_throttle_events += 1
            if radiation_faulted:
                radiation_fault_events += 1

        num_nodes = len(context.node_registry)
        models = (
            [m.__class__.__name__ for m in context.physics_orchestrator.models]
            if context.physics_orchestrator is not None
            else []
        )
        return {
            "thermal_throttle_events": thermal_throttle_events,
            "radiation_fault_events": radiation_fault_events,
            "total_energy_consumed": total_energy,
            "avg_temperature": temp_sum / max(num_nodes, 1),
            "num_nodes": num_nodes,
            "active_models": models,
        }

    def name(self) -> str:
        return "physics"


STRATEGIES["physics"] = PhysicsMetricsCollector
