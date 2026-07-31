"""
Engines layer (L2) — shortest-path routing engine.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import List

import networkx as nx

from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class ShortestPathRouter(RoutingEngine):
    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        try:
            raw = nx.shortest_path(graph, source=source, target=destination, weight="quality")
            path: list[NodeId] = [NodeId(n) for n in raw]
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def name(self) -> str:
        return "shortest_path"


STRATEGIES["shortest_path"] = ShortestPathRouter
