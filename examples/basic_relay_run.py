from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes import GroundStation, RelayNode
from skynetra.engines.routing import ShortestPathRouter
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics import NetworkMetricsCollector, TopologyMetricsCollector


def main() -> None:
    nodes: Dict[NodeId, RelayNode | GroundStation] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
        NodeId("sat-3"): RelayNode(NodeId("sat-3")),
        NodeId("gs-1"): GroundStation(NodeId("gs-1")),
    }

    router = ShortestPathRouter()
    collectors = [NetworkMetricsCollector(), TopologyMetricsCollector()]

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        metrics_collectors=collectors,
        dt=1.0,
    )

    results = sim.run(duration=5.0)

    print(f"Simulation ran for {results.duration} seconds")
    print(f"Metrics keys: {list(results.metrics.keys())}")
    for name, data in results.metrics.items():
        print(f"  {name}: {data}")


if __name__ == "__main__":
    main()
