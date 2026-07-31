from __future__ import annotations

from typing import Any, Dict

from skynetra.foundation.types import NodeId
from skynetra.domain.nodes import RelayNode
from skynetra.engines.routing import ShortestPathRouter
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class LatencyMetricsCollector(MetricsCollector):
    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        total_hops = 0
        total_nodes = len(context.nodes)
        for node in context.nodes.values():
            total_hops += node.metrics.packets_sent
        return {
            "estimated_total_hops": total_hops,
            "node_count": total_nodes,
        }

    def name(self) -> str:
        return "latency_metrics"


def main() -> None:
    STRATEGIES["latency_metrics"] = LatencyMetricsCollector

    from typing import Dict

    nodes: Dict[NodeId, RelayNode] = {
        NodeId("a"): RelayNode(NodeId("a")),
        NodeId("b"): RelayNode(NodeId("b")),
        NodeId("c"): RelayNode(NodeId("c")),
    }

    router = ShortestPathRouter()
    collector = LatencyMetricsCollector()

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        metrics_collectors=[collector],
        dt=1.0,
    )
    results = sim.run(duration=3.0)

    print(f"Custom LatencyMetricsCollector simulation: {results.duration}s")
    print(f"Metrics: {results.metrics}")


if __name__ == "__main__":
    main()
