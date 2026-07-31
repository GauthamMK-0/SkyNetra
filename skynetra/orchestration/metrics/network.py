"""
Orchestration layer (L3) — network metrics collector.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Dict

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class NetworkMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        total_packets = sum(
            node.metrics.packets_sent + node.metrics.packets_received
            for node in context.nodes.values()
        )
        total_dropped = sum(
            node.metrics.packets_dropped for node in context.nodes.values()
        )
        return {
            "total_packets": total_packets,
            "total_dropped": total_dropped,
            "edge_count": context.topology_graph.number_of_edges(),
            "node_count": context.topology_graph.number_of_nodes(),
        }

    def name(self) -> str:
        return "network"


STRATEGIES["network"] = NetworkMetricsCollector
