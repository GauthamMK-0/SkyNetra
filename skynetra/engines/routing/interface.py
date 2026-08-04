"""
Engines layer (L2) — routing engine abstract interface.

Layer 2 interface for routing algorithms. Concrete strategies are
registered in registry.py as a static dict — no dynamic discovery.

A routing engine decides, for a packet at a node, which neighbor to
forward to. It reads only the Layer 1 shapes (Packet, nx.DiGraph with
the Layer 1 edge schema, Node registry with dict-based state) plus
plain weight_overrides dicts passed down by other Layer 2 engines —
it never imports Layer 3 or Layer 4.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import LinkId, NodeId


class RoutingEngine(ABC):
    """Layer 2 interface for routing algorithms. Concrete strategies are
    registered in registry.py as a static dict — no dynamic discovery.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    @abstractmethod
    def select_next_hop(
        self,
        packet: Packet,
        current_node_id: NodeId,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> NodeId | None:
        """Return the next-hop node id for `packet` at `current_node_id`,
        or None when no onward hop exists.
        """
        ...

    @abstractmethod
    def update_topology(self, new_graph: nx.DiGraph) -> None:
        """Notify the engine that the topology graph changed.

        Engines that precompute routing tables do so here.
        """
        ...

    def get_edge_weight(
        self,
        graph: nx.DiGraph,
        u: NodeId,
        v: NodeId,
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> float:
        """Base edge weight: propagation delay plus any per-link override.

        `weight_overrides` are plain dicts computed by other Layer 2
        engines (e.g. physics models) and passed down; this base method
        always uses them additively.
        """
        base = float(graph[u][v].get("propagation_delay_ms", 1.0))
        if weight_overrides:
            base += float(weight_overrides.get(LinkId(f"{u}->{v}"), 0.0))
        return base

    def filter_operational_nodes(
        self,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
    ) -> nx.DiGraph:
        """Subgraph restricted to nodes that are operational.

        Nodes with no registry entry are assumed operational (they carry
        no state we could query).
        """
        operational = [
            n
            for n in graph.nodes()
            if node_registry.get(n) is None or node_registry[n].is_operational()
        ]
        return graph.subgraph(operational)
