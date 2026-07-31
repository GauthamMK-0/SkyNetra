from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes import GroundStation, RelayNode
from skynetra.engines.routing import ShortestPathRouter
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics import NetworkMetricsCollector, TopologyMetricsCollector


def build_constellation(num_relays: int) -> Dict[NodeId, RelayNode | GroundStation]:
    nodes: Dict[NodeId, RelayNode | GroundStation] = {}
    for i in range(num_relays):
        nodes[NodeId(f"relay-{i}")] = RelayNode(NodeId(f"relay-{i}"))
    nodes[NodeId("gs-0")] = GroundStation(NodeId("gs-0"))
    return nodes


def main() -> None:
    sizes = [2, 4, 8, 16, 32]
    print(f"{'Num Nodes':>10} {'Edges':>8} {'Avg Degree':>10} {'Packets':>8} {'Dropped':>8}")
    print("-" * 50)

    for n in sizes:
        nodes = build_constellation(n)
        router = ShortestPathRouter()
        collectors = [NetworkMetricsCollector(), TopologyMetricsCollector()]

        sim = SkyNetraSimulation(
            nodes=nodes,
            routing_engine=router,
            metrics_collectors=collectors,
            dt=1.0,
        )
        results = sim.run(duration=10.0)

        net = results.metrics.get("network", {})
        topo = results.metrics.get("topology", {})

        print(
            f"{n:>10} "
            f"{topo.get('num_edges', 0):>8} "
            f"{topo.get('avg_degree', 0.0):>10.2f} "
            f"{net.get('total_packets', 0):>8} "
            f"{net.get('total_dropped', 0):>8}"
        )


if __name__ == "__main__":
    main()
