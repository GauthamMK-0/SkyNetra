"""
Engines layer (L2) — radiation physics model.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class RadiationModel(PhysicsModel):
    def __init__(self, background_dose_rate: float = 0.01) -> None:
        self._dose_rate = background_dose_rate

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        result = {}
        for nid, state in states.items():
            result[nid] = PhysicsState(
                position=state.position,
                velocity=state.velocity,
                temperature=state.temperature,
                radiation_dose=state.radiation_dose + self._dose_rate * dt,
                power_available=state.power_available,
                power_consumed=state.power_consumed,
            )
        return result

    def name(self) -> str:
        return "radiation"


STRATEGIES["radiation"] = RadiationModel
