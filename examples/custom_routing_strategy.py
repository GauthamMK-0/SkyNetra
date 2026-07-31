from __future__ import annotations

from typing import Dict, List

import networkx as nx

from skynetra.domain.nodes import RelayNode
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics import NetworkMetricsCollector


class SimpleHopRouter(RoutingEngine):
    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        if source not in graph or destination not in graph:
            return []
        try:
            return nx.shortest_path(graph, source=source, target=destination)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def name(self) -> str:
        return "simple_hop"


def main() -> None:
    STRATEGIES["simple_hop"] = SimpleHopRouter

    nodes: Dict[NodeId, RelayNode] = {
        NodeId("a"): RelayNode(NodeId("a")),
        NodeId("b"): RelayNode(NodeId("b")),
        NodeId("c"): RelayNode(NodeId("c")),
    }

    router = SimpleHopRouter()
    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        metrics_collectors=[NetworkMetricsCollector()],
        dt=1.0,
    )
    results = sim.run(duration=3.0)

    print(f"Custom SimpleHopRouter simulation: {results.duration}s")
    print(f"Metrics: {results.metrics}")


if __name__ == "__main__":
    main()
