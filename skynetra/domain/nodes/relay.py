"""
Domain layer (L1) — relay satellite node.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from skynetra.domain.nodes.base import Node
from skynetra.foundation.types import NodeId


class RelayNode(Node):
    def __init__(self, node_id: NodeId) -> None:
        super().__init__(node_id, node_type="relay")

    def step(self, dt: float) -> None:
        pass
