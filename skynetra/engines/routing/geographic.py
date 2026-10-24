"""
Engines layer (L2) — geographic greedy routing engine (GPSR-Space).

Stateless localized 3D ECI distance-to-target greedy routing.
At each forwarding step, a node selects the operational neighbor that
minimizes Euclidean distance to the packet's destination in 3D space.
If a local minimum is reached (no neighbor is closer to destination than
the current node), it falls back to the neighbor with the minimum propagation
delay to maintain forward progress.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId


class GeographicGreedyRouter(RoutingEngine):
    """Geographic Greedy Router for satellite constellations (GPSR-Space).

    Greedily advances packets toward the 3D ECI destination coordinates.
    Stateless and localized: requires no global routing table exchange.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._fallback_to_min_delay = bool(
            self._config.get("fallback_to_min_delay", True)
        )
        self._avoid_faulty_nodes = bool(
            self._config.get("avoid_faulty_nodes", True)
        )

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        # Geographic routing is stateless; position lookups happen live from graph
        pass

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

        # Direct connection to destination
        if graph.has_edge(current_node_id, packet.dst):
            dst_node = node_registry.get(packet.dst)
            if dst_node is None or dst_node.is_operational():
                return packet.dst

        # Get operational candidates
        candidates = [
            nbr
            for nbr in graph.successors(current_node_id)
            if not self._avoid_faulty_nodes
            or node_registry.get(nbr) is None
            or node_registry[nbr].is_operational()
        ]
        if not candidates:
            return None

        # Look up 3D positions from graph attributes
        dst_pos = graph.nodes.get(packet.dst, {}).get("position")
        curr_pos = graph.nodes.get(current_node_id, {}).get("position")

        if dst_pos is None or curr_pos is None:
            # Fallback to minimum delay if positions are missing
            return self._min_delay_neighbor(
                graph, current_node_id, candidates, node_registry, weight_overrides
            )

        curr_dist = math.dist(curr_pos, dst_pos)
        best_neighbor: NodeId | None = None
        min_dist = curr_dist

        for nbr in candidates:
            nbr_pos = graph.nodes.get(nbr, {}).get("position")
            if nbr_pos is None:
                continue
            dist = math.dist(nbr_pos, dst_pos)
            if dist < min_dist:
                min_dist = dist
                best_neighbor = nbr

        if best_neighbor is not None:
            return best_neighbor

        # Local minimum: no neighbor is strictly closer to destination than current node.
        # Deflection / perimeter fallback to neighbor with lowest link delay + override.
        if self._fallback_to_min_delay:
            return self._min_delay_neighbor(
                graph, current_node_id, candidates, node_registry, weight_overrides
            )

        return None

    def _min_delay_neighbor(
        self,
        graph: nx.DiGraph,
        u: NodeId,
        candidates: list[NodeId],
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> NodeId | None:
        best_nbr = None
        min_weight = float("inf")
        for v in candidates:
            weight = self.get_edge_weight(graph, u, v, node_registry, weight_overrides)
            if weight < min_weight:
                min_weight = weight
                best_nbr = v
        return best_nbr
