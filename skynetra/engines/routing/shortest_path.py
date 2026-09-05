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

import math
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

        # Fast path: precomputed table lookup when no overrides and candidate is operational
        if not weight_overrides:
            current_node = node_registry.get(current_node_id)
            if current_node is not None and not current_node.is_operational():
                return None
            next_hop = self._next_hop.get(current_node_id, {}).get(packet.dst)
            if next_hop is not None:
                next_node = node_registry.get(next_hop)
                if (
                    next_node is None or next_node.is_operational()
                ) and graph.has_edge(current_node_id, next_hop):
                    return next_hop

        operational_graph = self.filter_operational_nodes(graph, node_registry)
        if current_node_id not in operational_graph:
            return None
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
            transit = self._transit_subgraph(graph, source)
            try:
                lengths, paths = nx.single_source_dijkstra(
                    transit, source, weight=weight_fn
                )
            except nx.NetworkXError:
                lengths, paths = {}, {}
            targets: dict[NodeId, NodeId] = {}
            for target in lengths:
                route = paths[target]
                if len(route) > 1:
                    targets[target] = route[1]
            self._patch_pod_targets(graph, source, lengths, paths, targets)
            next_hop[source] = targets
        return next_hop

    def _transit_subgraph(
        self, graph: nx.DiGraph, keep: NodeId
    ) -> nx.DiGraph:
        """Subgraph with pod nodes removed except `keep`.

        Pods are compute endpoints: routing may start at a pod but never
        pass through one (L3 drops pod transit).
        """
        return graph.subgraph(
            [
                n
                for n in graph.nodes()
                if graph.nodes[n].get("node_type") != "pod" or n == keep
            ]
        )

    def _patch_pod_targets(
        self,
        graph: nx.DiGraph,
        source: NodeId,
        lengths: dict[NodeId, float],
        paths: dict[NodeId, list[NodeId]],
        targets: dict[NodeId, NodeId],
    ) -> None:
        """Fill next hops for pod destinations.

        A pod is reached via its attached satellite with the shortest
        distance; if `source` is itself attached to the pod, the direct
        edge is the next hop.
        """
        weight_fn = self._edge_weight_fn()
        for pod in graph.nodes():
            if graph.nodes[pod].get("node_type") != "pod" or pod == source:
                continue
            attached = list(graph.predecessors(pod))
            if not attached:
                continue
            best_sat = min(
                attached,
                key=lambda s: lengths.get(s, math.inf)
                + weight_fn(s, pod, graph.edges[s, pod]),
            )
            if best_sat not in lengths:
                continue
            if best_sat == source:
                targets[pod] = pod
            else:
                route = paths[best_sat]
                if len(route) > 1:
                    targets[pod] = route[1]

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
        if graph.nodes[target].get("node_type") == "pod":
            transit = self._transit_subgraph(graph, source)
            try:
                lengths, paths = nx.single_source_dijkstra(
                    transit, source, weight=self._edge_weight_fn(weight_overrides)
                )
            except nx.NetworkXError:
                return None
            targets: dict[NodeId, NodeId] = {}
            self._patch_pod_targets(graph, source, lengths, paths, targets)
            return targets.get(target)
        weight_fn = self._edge_weight_fn(weight_overrides)
        try:
            route = nx.dijkstra_path(graph, source, target, weight=weight_fn)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        if len(route) < 2:
            return None
        return cast(NodeId, route[1])
