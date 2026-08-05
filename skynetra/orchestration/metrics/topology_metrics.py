"""
Orchestration layer (L3) — topology metrics collector.

Reports graph size/degree plus the current `topology_version` so
consumers can see how often the L3 engine refreshed the topology.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class TopologyMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> dict[str, Any]:
        graph = context.graph
        if graph.number_of_nodes() == 0:
            avg_degree = 0.0
        else:
            degrees = [d for _, d in graph.degree()]
            avg_degree = sum(degrees) / len(degrees)
        return {
            "avg_degree": avg_degree,
            "num_edges": graph.number_of_edges(),
            "num_nodes": graph.number_of_nodes(),
            "topology_version": context.topology_version,
        }

    def name(self) -> str:
        return "topology"


STRATEGIES["topology"] = TopologyMetricsCollector
