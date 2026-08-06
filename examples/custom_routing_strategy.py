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
from skynetra.foundation.types import LinkId, NodeId
from skynetra.orchestration.engine import OrbitDCSimulation


class SimpleHopRouter(RoutingEngine):
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
        try:
            route = nx.shortest_path(graph, source=current_node_id, target=packet.dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        return route[1] if len(route) > 1 else None

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

    sim = OrbitDCSimulation.from_layers(
        constellation=constellation,
        node_registry=node_registry,
        routing_engine=SimpleHopRouter(),
        sim_duration_s=30.0,
        seed=42,
    )
    results = sim.run()

    print(f"Custom SimpleHopRouter simulation: {results.duration}s")
    print(f"Metrics: {results.engine_metrics}")


if __name__ == "__main__":
    main()
