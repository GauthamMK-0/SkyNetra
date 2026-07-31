from __future__ import annotations

from typing import Any, Dict

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class FLMetricsCollector(MetricsCollector):
    def __init__(self) -> None:
        self._round_count: int = 0

    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        self._round_count += 1
        total_compute = sum(
            node.metrics.compute_flops for node in context.nodes.values()
        )
        total_energy = sum(
            node.metrics.energy_consumed for node in context.nodes.values()
        )
        return {
            "fl_round": self._round_count,
            "participating_nodes": len(context.nodes),
            "total_compute_flops": total_compute,
            "total_energy_consumed": total_energy,
        }

    def name(self) -> str:
        return "fl_metrics"


STRATEGIES["fl_metrics"] = FLMetricsCollector
