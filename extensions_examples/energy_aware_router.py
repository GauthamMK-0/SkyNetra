from __future__ import annotations

from typing import Dict, List

import networkx as nx

from skynetra.foundation.types import NodeId
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES


class EnergyAwareRouter(RoutingEngine):
    def __init__(self, power_weights: Dict[NodeId, float] | None = None) -> None:
        self._power_weights: Dict[NodeId, float] = power_weights or {}

    def set_power_weight(self, node_id: NodeId, available_power: float) -> None:
        self._power_weights[node_id] = available_power

    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        if source not in graph or destination not in graph:
            return []

        best_path: List[NodeId] = []
        best_score: float = -1.0

        for path in nx.all_simple_paths(
            graph, source=source, target=destination, cutoff=10
        ):
            total_power = sum(
                self._power_weights.get(n, 0.0) for n in path
            )
            score = total_power / max(len(path), 1)
            if score > best_score:
                best_score = score
                best_path = path

        return best_path

    def name(self) -> str:
        return "energy_aware"


STRATEGIES["energy_aware"] = EnergyAwareRouter
