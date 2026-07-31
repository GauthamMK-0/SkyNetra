"""
Engines layer (L2) — routing engine abstract interface.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

import networkx as nx

from skynetra.foundation.types import NodeId


class RoutingEngine(ABC):
    @abstractmethod
    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
