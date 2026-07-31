"""
Engines layer (L2) — physics model abstract interface.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.foundation.types import NodeId


class PhysicsModel(ABC):
    @abstractmethod
    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
