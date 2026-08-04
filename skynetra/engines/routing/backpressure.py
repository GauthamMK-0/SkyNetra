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

    @property
    def params(self) -> BackPressureConfig:
        return self._params

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        # Backpressure is stateless across topology changes: the graph is
        # re-read at every decision. Nothing to precompute.
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
        decision_graph = graph
        if self._params.avoid_faulty_nodes:
            decision_graph = self.filter_operational_nodes(graph, node_registry)
        if current_node_id not in decision_graph:
            return None

        candidates: list[NodeId] = list(decision_graph.successors(current_node_id))
        if not candidates:
            return None

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

        return min(candidates, key=total_weight)

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
