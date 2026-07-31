"""
Orchestration layer (L3) — physics metrics collector.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Dict

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class PhysicsMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        total_energy = sum(
            node.metrics.energy_consumed for node in context.nodes.values()
        )
        avg_temp = (
            sum(node.physics.temperature for node in context.nodes.values())
            / max(len(context.nodes), 1)
        )
        return {
            "total_energy_consumed": total_energy,
            "avg_temperature": avg_temp,
            "num_nodes": len(context.nodes),
        }

    def name(self) -> str:
        return "physics"


STRATEGIES["physics"] = PhysicsMetricsCollector
