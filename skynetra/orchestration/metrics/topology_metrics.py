"""
Orchestration layer (L3) — topology metrics collector.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Dict

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class TopologyMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        g = context.topology_graph
        if g.number_of_nodes() == 0:
            return {"avg_degree": 0.0, "num_edges": 0, "num_nodes": 0}
        degrees = [d for _, d in g.degree()]
        avg_degree = sum(degrees) / len(degrees)
        return {
            "avg_degree": avg_degree,
            "num_edges": g.number_of_edges(),
            "num_nodes": g.number_of_nodes(),
        }

    def name(self) -> str:
        return "topology"


STRATEGIES["topology"] = TopologyMetricsCollector
