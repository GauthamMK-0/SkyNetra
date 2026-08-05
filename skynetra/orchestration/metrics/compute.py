"""
Orchestration layer (L3) — compute metrics collector.

Sums the compute task/FLOPS/energy counters accumulated in pod nodes'
`metrics_state` over the run.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class ComputeMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> dict[str, Any]:
        total_tasks = 0
        total_flops = 0.0
        total_energy = 0.0
        for node in context.node_registry.values():
            if node.node_type != "pod":
                continue
            total_tasks += node.metrics_state["compute_tasks"]
            total_flops += node.metrics_state["compute_flops"]
            total_energy += node.metrics_state["energy_consumed"]
        return {
            "total_compute_tasks": total_tasks,
            "total_compute_flops": total_flops,
            "total_energy_consumed": total_energy,
            "num_pods": len(context.pod_ids),
        }

    def name(self) -> str:
        return "compute"


STRATEGIES["compute"] = ComputeMetricsCollector
