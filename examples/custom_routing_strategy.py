"""
How to write and use a custom `RoutingEngine` without touching the
`skynetra` source: `SimpleHopRouter` uses unweighted BFS.

It implements the two ABC methods (`select_next_hop`, `update_topology`),
is registered in the L2 strategy registry, and is passed to the
simulation as an instance via `OrbitDCSimulation.from_layers` (the L4
`FullConfig` routing field is a closed Literal by design, so custom
engines plug in at the L3 constructor boundary instead).

Run:  python examples/custom_routing_strategy.py
"""

from __future__ import annotations

from collections import defaultdict

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import ReferenceCircularPropagator
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES
from skynetra.engines.workload.inference import InferenceQueryWorkload
from skynetra.foundation.types import LinkId, NodeId
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector
from skynetra.orchestration.metrics.network import NetworkMetricsCollector


class SimpleHopRouter(RoutingEngine):
    """Custom router: calculates unweighted minimum-hop paths via BFS."""

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config)
        self.decisions_made = 0
        self.routes_by_destination: dict[str, int] = defaultdict(int)
        self.forwarding_edges: dict[tuple[str, str], int] = defaultdict(int)
        self.no_path_count = 0

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        return None

    def select_next_hop(
        self,
        packet: Packet,
        current_node_id: NodeId,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> NodeId | None:
        if current_node_id == packet.dst:
            return None
        self.decisions_made += 1
        try:
            route = nx.shortest_path(graph, source=current_node_id, target=packet.dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.no_path_count += 1
            return None
        if len(route) > 1:
            next_hop = route[1]
            self.routes_by_destination[str(packet.dst)] += 1
            self.forwarding_edges[(str(current_node_id), str(next_hop))] += 1
            return next_hop
        return None

    def name(self) -> str:
        return "simple_hop"


def main() -> None:
    STRATEGIES["simple_hop"] = SimpleHopRouter

    constellation = ConstellationConfig(
        n_planes=3, sats_per_plane=6, altitude_km=550.0, inclination_deg=55.0
    )
    propagator = ReferenceCircularPropagator()
    node_registry: dict[NodeId, Node] = {
        sat_id: RelayNode(sat_id) for sat_id in propagator.get_sat_ids(constellation)
    }
    for i in range(2):
        node_registry[NodeId(f"pod-{i + 1}")] = PodNode(NodeId(f"pod-{i + 1}"))
    node_registry[NodeId("gs-1")] = GroundStationNode(NodeId("gs-1"))

    # Active workload to exercise the custom routing algorithm
    workload = InferenceQueryWorkload({
        "mean_interval_s": 3.0,
        "query_size_bytes": 512,
        "flops_required": 1e9,
        "seed": 42,
    })

    router = SimpleHopRouter()

    print("Running Custom SimpleHopRouter Simulation (60.0s)...")
    sim = OrbitDCSimulation.from_layers(
        constellation=constellation,
        node_registry=node_registry,
        routing_engine=router,
        workloads=[workload],
        metrics_collectors=[NetworkMetricsCollector(), ComputeMetricsCollector()],
        sim_duration_s=60.0,
        seed=42,
    )
    results = sim.run()

    net = results.engine_metrics.get("network_metrics", {})
    comp = results.engine_metrics.get("compute_metrics", {})

    transmitted = net.get("transmitted", 0)
    delivered = net.get("delivered", 0)
    dropped = net.get("dropped", 0)
    avg_latency_ms = net.get("avg_latency_s", 0.0) * 1000
    loss_rate = (dropped / max(1, transmitted)) * 100
    delivery_rate = (delivered / max(1, delivered + dropped)) * 100

    print("\n" + "=" * 70)
    print("               SKYNETRA CUSTOM ROUTING STRATEGY REPORT                ")
    print("=" * 70)
    print("Architecture Overview:")
    print("  * Routing Strategy  : SimpleHopRouter (Custom Layer 2 Implementation)")
    print("  * Path Computation  : Unweighted Breadth-First-Search (BFS) Next-Hop")
    print("  * Constellation     : 18 Relay Satellites, 2 Compute Pods, 1 Ground Station")
    print(f"  * Simulation Length : {results.duration:.1f} simulated seconds")

    print("\n[Routing Engine Telemetry]")
    print(f"  * Total Routing Decisions Made : {router.decisions_made} hop evaluations")
    print(f"  * Routing Failures (No Path)   : {router.no_path_count}")
    print("  * Routing By Destination Pod   :")
    for dst, count in router.routes_by_destination.items():
        print(f"      - {dst:<8} : {count:>2} forwarding steps")

    print("\n[End-to-End Network Metrics]")
    print(f"  * Packets Injected/Transmitted : {transmitted}")
    print(f"  * Packets Delivered to Pods    : {delivered}")
    print(f"  * Packets Dropped              : {dropped}")
    print(f"  * Packet Loss Rate             : {loss_rate:.2f}%")
    print(f"  * Delivery Completion Rate     : {delivery_rate:.2f}%")
    print(f"  * Mean End-to-End Latency      : {avg_latency_ms:.2f} ms")

    print("\n[On-Orbit Compute Servicing]")
    print(f"  * Inference Jobs Finished      : {comp.get('compute_jobs_completed', 0)} tasks")
    comp_flops = comp.get('compute_flops_completed', 0.0)
    print(f"  * Total FLOPs Accrued          : {comp_flops:.2e} FLOPS")
    comp_lat_ms = comp.get('avg_compute_latency_s', 0.0) * 1000
    print(f"  * Mean Task Service Time       : {comp_lat_ms:.2f} ms")
    print("=" * 70)


if __name__ == "__main__":
    main()
