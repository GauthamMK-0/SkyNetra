"""
Engines layer (L2) — thermal physics model.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class ThermalModel(PhysicsModel):
    def __init__(self, albedo: float = 0.3, emissivity: float = 0.8) -> None:
        self._albedo = albedo
        self._emissivity = emissivity

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        result = {}
        for nid, state in states.items():
            equil = 300.0
            delta = (equil - state.temperature) * 0.01 * dt
            result[nid] = PhysicsState(
                position=state.position,
                velocity=state.velocity,
                temperature=state.temperature + delta,
                radiation_dose=state.radiation_dose,
                power_available=state.power_available,
                power_consumed=state.power_consumed,
            )
        return result

    def name(self) -> str:
        return "thermal"


STRATEGIES["thermal"] = ThermalModel
