"""
Orchestration layer (L3) — compute metrics collector.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Dict

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class ComputeMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        total_tasks = sum(
            node.metrics.compute_tasks for node in context.nodes.values()
        )
        total_flops = sum(
            node.metrics.compute_flops for node in context.nodes.values()
        )
        return {
            "total_compute_tasks": total_tasks,
            "total_compute_flops": total_flops,
            "num_nodes": len(context.nodes),
        }

    def name(self) -> str:
        return "compute"


STRATEGIES["compute"] = ComputeMetricsCollector
