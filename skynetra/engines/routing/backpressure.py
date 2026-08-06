"""
Engines layer (L2) — backpressure routing engine.

Load-aware router:

    w(u,v) = alpha*delay + beta*hop_cost + gamma*queue_pressure(v)
             + delta*compute_backlog(v) + epsilon*physics_penalty(u,v)
             + weight_overrides

Queue pressure and compute backlog are read from the Layer 1 node API
(get_utilization / get_queue_depth), never from Layer 3. The physics
penalty comes exclusively from the plain `weight_overrides` dicts
passed down by Layer 2 physics engines — it is exactly 0 when the
overrides are empty or None, so composing this router without physics
engines costs nothing.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId


@dataclass
class BackPressureConfig:
    alpha: float = 1.0
    beta: float = 5.0
    gamma: float = 50.0
    delta: float = 30.0
    epsilon: float = 1.0
    kappa_thermal: float = 20.0
    kappa_radiation: float = 1000.0
    avoid_faulty_nodes: bool = True


class BackPressureRouter(RoutingEngine):
    """Load-aware router: w(u,v) = alpha*delay + beta*hop_cost +
    gamma*queue_pressure(v) + delta*compute_backlog(v) +
    epsilon*physics_penalty(u,v) + weight_overrides.
    physics_penalty defaults to 0 when overrides are empty — no
    overhead when physics engines (Layer 2 physics) are not composed
    into the running simulation.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._params = BackPressureConfig(**self._config)
        # Cached per-topology view: (cache_key, (operational subgraph,
        # all-pairs reachability, all-pairs BFS hop distances)). Built
        # once per topology rebuild (and on fault-state changes) instead
        # of running a BFS per candidate per hop.
        self._view_cache: tuple[
            tuple[int, frozenset[NodeId]],
            tuple[nx.DiGraph, dict[NodeId, frozenset[NodeId]], dict[NodeId, dict[NodeId, int]]],
        ] | None = None

    @property
    def params(self) -> BackPressureConfig:
        return self._params

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        # The operational subgraph and routing tables are rebuilt lazily
        # from the live graph; a topology change invalidates the cache.
        self._view_cache = None

    def _operational_view(
        self,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
    ) -> tuple[
        nx.DiGraph,
        dict[NodeId, frozenset[NodeId]],
        dict[NodeId, dict[NodeId, int]],
    ]:
        """Cached (operational subgraph, reachability, hop distances).

        The key combines the graph identity with the set of faulted
        nodes, so fault-state changes mid-run rebuild automatically
        (rare) while steady-state decisions cost O(V) + O(1) lookups.
        """
        faulted = (
            frozenset(nid for nid, node in node_registry.items() if not node.is_operational())
            if self._params.avoid_faulty_nodes
            else frozenset()
        )
        key = (id(graph), faulted)
        if self._view_cache is not None and self._view_cache[0] == key:
            return self._view_cache[1]
        operational = graph.subgraph([n for n in graph.nodes() if n not in faulted])
        reachable, hop_distances = self._build_tables(operational)
        view = (operational, reachable, hop_distances)
        self._view_cache = (key, view)
        return view

    @staticmethod
    def _build_tables(
        graph: nx.DiGraph,
    ) -> tuple[dict[NodeId, frozenset[NodeId]], dict[NodeId, dict[NodeId, int]]]:
        """All-pairs reachability and BFS hop distances (O(V·(V+E)))."""
        reachable: dict[NodeId, frozenset[NodeId]] = {}
        hop_distances: dict[NodeId, dict[NodeId, int]] = {}
        for start in graph.nodes():
            seen = {start}
            distances = {start: 0}
            frontier = [start]
            while frontier:
                next_frontier: list[NodeId] = []
                for node in frontier:
                    depth = distances[node]
                    for nxt in graph.successors(node):
                        if nxt not in seen:
                            seen.add(nxt)
                            distances[nxt] = depth + 1
                            next_frontier.append(nxt)
                frontier = next_frontier
            reachable[start] = frozenset(seen)
            hop_distances[start] = distances
        return reachable, hop_distances

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
        decision_graph, reachable, hop_distances = self._operational_view(
            graph, node_registry
        )
        if current_node_id not in decision_graph:
            return None

        candidates: list[NodeId] = list(decision_graph.successors(current_node_id))
        if not candidates:
            return None

        if packet.dst in candidates:
            return packet.dst

        # Greedy per-hop decisions oscillate on ties and can route into
        # dead-ends (e.g. a ground station whose only edge points back)
        # or around closed rings when loads are static.
        # 1) only consider successors from which the destination is
        #    reachable;
        # 2) prefer nodes this packet has not visited yet (cycle
        #    breaker, backed by the L3-maintained path_history);
        # 3) refuse the immediate U-turn (the node we just came from);
        # 4) never pick a pod that is not the destination (L3 forbids
        #    pod transit) — all while alternatives exist.
        dst = packet.dst
        reachable_from = reachable
        reachable_candidates = [
            c for c in candidates if dst in reachable_from[c]
        ]
        if reachable_candidates:
            candidates = reachable_candidates
        if dst not in candidates:
            non_pods = [
                c
                for c in candidates
                if node_registry.get(c, None) is None
                or node_registry[c].node_type != "pod"
            ]
            if non_pods:
                candidates = non_pods
        if len(packet.path_history) >= 2:
            previous = packet.path_history[-2]
            others = [c for c in candidates if str(c) != previous]
            if others:
                candidates = others
        visited = set(packet.path_history)
        fresh = [c for c in candidates if str(c) not in visited]
        if fresh:
            candidates = fresh
        def total_weight(v: NodeId) -> float:
            base = self.get_edge_weight(
                decision_graph, current_node_id, v, node_registry, None
            )
            penalty = self.physics_penalty(current_node_id, v, weight_overrides)
            return (
                self._params.alpha * base
                + self._params.beta * 1.0
                + self._params.gamma * self._queue_pressure(v, node_registry)
                + self._params.delta * self._compute_backlog(v, node_registry)
                + self._params.epsilon * penalty
            )

        # Tie-break toward the destination so that equal-weight loads
        # cannot lock packets into closed rings.
        def rank(v: NodeId) -> tuple[float, int]:
            return total_weight(v), hop_distances[v].get(dst, 10**6)

        return min(candidates, key=rank)

    def physics_penalty(
        self,
        u: NodeId,
        v: NodeId,
        weight_overrides: dict[LinkId, float] | None,
    ) -> float:
        """Physics penalty for edge u->v, read from `weight_overrides`.

        Exactly 0.0 when `weight_overrides` is empty or None — Layer 2
        physics engines pass plain dicts DOWN into this method.
        """
        if not weight_overrides:
            return 0.0
        return float(weight_overrides.get(LinkId(f"{u}->{v}"), 0.0))

    def _queue_pressure(
        self, node_id: NodeId, node_registry: dict[NodeId, Node]
    ) -> float:
        node = node_registry.get(node_id)
        if node is None:
            return 0.0
        return float(node.get_utilization())

    def _compute_backlog(
        self, node_id: NodeId, node_registry: dict[NodeId, Node]
    ) -> float:
        node = node_registry.get(node_id)
        if node is None or node.node_type != "pod":
            return 0.0
        return float(node.get_queue_depth())
