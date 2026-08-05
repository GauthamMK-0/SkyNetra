"""
Worked example: extending the routing layer WITHOUT modifying
`skynetra/engines/routing/registry.py`. This is the recommended pattern
for third-party code in a layered architecture: depend only on the
public interface, compose explicitly via `from_layers()`.

The strategy below subclasses the L2 `RoutingEngine` ABC, implements
`select_next_hop` / `update_topology`, and overrides `get_edge_weight`
to penalize hops toward nodes whose `power_available_w` state is below
a threshold — the L2 interface passes physics state around as plain
dicts, so the router reads `node.physics_state` directly.

Two composition paths, both shown in the docstring (NOT executed at
import time — importing this module has no side effects):

(a) Register into your OWN copy of the strategy map and pass strings:
        from skynetra.engines.routing import registry as routing_registry
        routing_registry.STRATEGIES["energy_aware"] = EnergyAwareRouter
    (mutating the shared dict at process start — acceptable for a
    single-process script, documented as an advanced/unsafe pattern)

(b) PREFERRED: bypass string registries entirely —
        sim = OrbitDCSimulation.from_layers(
            ...,
            routing_engine=EnergyAwareRouter({"power_threshold_w": 150.0}),
            ...)
    The engine calls `select_next_hop` on the instance directly, so
    no registry entry is needed.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId


class EnergyAwareRouter(RoutingEngine):
    """Penalizes routing through nodes with low `power_available_w`.

    Implements `select_next_hop` with a live Dijkstra over the
    operational subgraph using `get_edge_weight`, so the power penalty
    always applies (no precomputed tables to go stale). Config keys:
    `power_threshold_w` (default 100.0) and `penalty` (default 500.0,
    added to the base edge weight when the target node is power-starved).
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.power_threshold_w = float(self._config.get("power_threshold_w", 100.0))
        self.penalty = float(self._config.get("penalty", 500.0))
        self._topology: nx.DiGraph | None = None

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        # Stateless router: nothing to precompute. Kept for the ABC
        # contract; the ShortestPathRouter uses this hook to build
        # routing tables, which is where cache-style routers would too.
        self._topology = new_graph

    def get_edge_weight(
        self,
        graph: nx.DiGraph,
        u: NodeId,
        v: NodeId,
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> float:
        base = super().get_edge_weight(graph, u, v, node_registry, weight_overrides)
        node = node_registry.get(v)
        if node is not None and node.physics_state["power_available_w"] < self.power_threshold_w:
            base += self.penalty
        return base

    def select_next_hop(
        self,
        packet: Packet,
        current_node_id: NodeId,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> NodeId | None:
        operational = self.filter_operational_nodes(graph, node_registry)
        if current_node_id not in operational or packet.dst not in operational:
            return None
        try:
            path = nx.shortest_path(
                operational,
                source=current_node_id,
                target=packet.dst,
                weight=lambda u, v, _d: self.get_edge_weight(
                    operational, u, v, node_registry, weight_overrides
                ),
            )
        except nx.NetworkXNoPath:
            return None
        if len(path) < 2:
            return None
        return path[1]
