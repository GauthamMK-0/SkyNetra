"""
Engines layer (L2) — physics orchestrator.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict, List

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.foundation.types import NodeId


class PhysicsOrchestrator(PhysicsModel):
    def __init__(self, models: List[PhysicsModel]) -> None:
        self._models = models

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        current = states
        for model in self._models:
            current = model.apply(current, dt)
        return current

    def name(self) -> str:
        return "orchestrator"
