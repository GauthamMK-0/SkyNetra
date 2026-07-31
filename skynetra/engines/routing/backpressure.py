"""
Engines layer (L2) — backpressure routing engine.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict, List

import networkx as nx

from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class BackPressureRouter(RoutingEngine):
    def __init__(self) -> None:
        self._queue_backlog: Dict[str, float] = {}

    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        path = [source]
        current = source
        visited = {current}
        for _ in range(len(graph)):
            neighbors = list(graph.neighbors(current))
            if destination in neighbors:
                path.append(destination)
                break
            best = max(
                (n for n in neighbors if n not in visited),
                key=lambda n: self._queue_backlog.get(f"{current}->{n}", 0.0),
                default=None,
            )
            if best is None:
                break
            visited.add(best)
            path.append(best)
            current = best
            if current == destination:
                break
        return path if path[-1] == destination else []

    def name(self) -> str:
        return "backpressure"

    def update_backlog(self, edge_key: str, delta: float) -> None:
        self._queue_backlog[edge_key] = (
            self._queue_backlog.get(edge_key, 0.0) + delta
        )


STRATEGIES["backpressure"] = BackPressureRouter
