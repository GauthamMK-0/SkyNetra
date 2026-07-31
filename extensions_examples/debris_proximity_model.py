from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class DebrisProximityModel(PhysicsModel):
    def __init__(self, debris_dose_rate: float = 0.2) -> None:
        self._debris_dose_rate = debris_dose_rate

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        new_states: Dict[NodeId, PhysicsState] = {}
        for nid, state in states.items():
            new_states[nid] = PhysicsState(
                position=state.position,
                velocity=state.velocity,
                temperature=state.temperature,
                radiation_dose=state.radiation_dose + self._debris_dose_rate * dt,
                power_available=state.power_available,
                power_consumed=state.power_consumed,
            )
        return new_states

    def name(self) -> str:
        return "debris_proximity"


STRATEGIES["debris_proximity"] = DebrisProximityModel
