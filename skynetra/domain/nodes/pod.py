"""
Domain layer (L1) — compute pod node.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from skynetra.domain.nodes.base import Node
from skynetra.foundation.types import NodeId


class PodNode(Node):
    def __init__(
        self,
        node_id: NodeId,
        flops: float = 1e12,
        memory_gb: float = 16.0,
        storage_gb: float = 100.0,
    ) -> None:
        super().__init__(node_id, node_type="pod")
        self._flops = flops
        self._memory_gb = memory_gb
        self._storage_gb = storage_gb

    @property
    def flops(self) -> float:
        return self._flops

    @property
    def memory_gb(self) -> float:
        return self._memory_gb

    @property
    def storage_gb(self) -> float:
        return self._storage_gb

    def step(self, dt: float) -> None:
        pass
