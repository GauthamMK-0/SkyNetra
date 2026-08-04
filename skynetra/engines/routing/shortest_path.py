"""
Engines layer (L2) — shortest-path routing engine.

Dijkstra baseline. Precomputes all-pairs next-hop tables on topology
update. weight_mode: 'delay'|'hops'|'capacity'.

Weight modes:
    delay     — propagation_delay_ms (the RoutingEngine base weight)
    hops      — 1.0 per edge
    capacity  — inverse of the edge capacity (higher capacity wins)

When `weight_overrides` are supplied to `select_next_hop` (e.g. physics
penalties from another Layer 2 engine), the precomputed tables do not
reflect them, so a live Dijkstra over the operational subgraph is run
with the overrides applied. The tables otherwise serve as the fast path.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId

WEIGHT_MODES = ("delay", "hops", "capacity")
DEFAULT_WEIGHT_MODE = "delay"

WeightFn = Callable[[NodeId, NodeId, dict[str, Any]], float]


class ShortestPathRouter(RoutingEngine):
    """Dijkstra baseline. Precomputes all-pairs next-hop tables on
    topology update. weight_mode: 'delay'|'hops'|'capacity'.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        weight_mode = self._config.get("weight_mode", DEFAULT_WEIGHT_MODE)
        if weight_mode not in WEIGHT_MODES:
            raise ValueError(
                f"Unknown weight_mode '{weight_mode}'. "
                f"Available: {list(WEIGHT_MODES)}"
            )
        self._weight_mode = weight_mode
        self._next_hop: dict[NodeId, dict[NodeId, NodeId]] = {}

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        self._next_hop = self._precompute_next_hops(new_graph)

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
        operational_graph = self.filter_operational_nodes(graph, node_registry)
        if current_node_id not in operational_graph:
            return None
        if not weight_overrides:
            next_hop = self._next_hop.get(current_node_id, {}).get(packet.dst)
            if next_hop is not None and operational_graph.has_node(next_hop):
                return next_hop
        return self._dijkstra_next_hop(
            operational_graph, current_node_id, packet.dst, weight_overrides
        )

    def _edge_weight_fn(
        self, weight_overrides: dict[LinkId, float] | None = None
    ) -> WeightFn:
        if self._weight_mode == "hops":
            return lambda u, v, attrs: 1.0
        if self._weight_mode == "capacity":
            return lambda u, v, attrs: 1.0 / max(
                float(attrs.get("capacity", 1.0)), 1e-9
            )
        if weight_overrides:

            def delay_with_overrides(
                u: NodeId, v: NodeId, attrs: dict[str, Any]
            ) -> float:
                base = float(attrs.get("propagation_delay_ms", 1.0))
                return base + float(weight_overrides.get(LinkId(f"{u}->{v}"), 0.0))

            return delay_with_overrides
        return lambda u, v, attrs: float(attrs.get("propagation_delay_ms", 1.0))

    def _precompute_next_hops(self, graph: nx.DiGraph) -> dict[NodeId, dict[NodeId, NodeId]]:
        next_hop: dict[NodeId, dict[NodeId, NodeId]] = {}
        weight_fn = self._edge_weight_fn()
        for source in graph.nodes():
            targets: dict[NodeId, NodeId] = {}
            try:
                lengths, paths = nx.single_source_dijkstra(
                    graph, source, weight=weight_fn
                )
            except nx.NetworkXError:
                lengths, paths = {}, {}
            for target in lengths:
                route = paths[target]
                if len(route) > 1:
                    targets[target] = route[1]
            next_hop[source] = targets
        return next_hop

    def _dijkstra_next_hop(
        self,
        graph: nx.DiGraph,
        source: NodeId,
        target: NodeId,
        weight_overrides: dict[LinkId, float] | None,
    ) -> NodeId | None:
        if source not in graph or target not in graph:
            return None
        if source == target:
            return None
        weight_fn = self._edge_weight_fn(weight_overrides)
        try:
            route = nx.dijkstra_path(graph, source, target, weight=weight_fn)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        if len(route) < 2:
            return None
        return cast(NodeId, route[1])
