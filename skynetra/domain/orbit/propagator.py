"""
Domain layer (L1) — propagator abstract interface.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from skynetra.foundation.types import NodeId, Vector3


class PropagatorInterface(ABC):
    @abstractmethod
    def propagate(
        self, positions: Dict[NodeId, Vector3], dt: float
    ) -> Dict[NodeId, Vector3]:
        ...

    @abstractmethod
    def get_epoch(self) -> float:
        ...

    @abstractmethod
    def set_epoch(self, epoch: float) -> None:
        ...

    @abstractmethod
    def reset(self, epoch: float) -> None:
        ...
