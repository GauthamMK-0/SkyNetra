"""
Engines layer (L2) — power physics model.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class PowerModel(PhysicsModel):
    def __init__(self, solar_panel_area: float = 10.0, efficiency: float = 0.3) -> None:
        self._panel_area = solar_panel_area
        self._efficiency = efficiency

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        result = {}
        solar_flux = 1361.0
        generated = solar_flux * self._panel_area * self._efficiency * dt
        for nid, state in states.items():
            result[nid] = PhysicsState(
                position=state.position,
                velocity=state.velocity,
                temperature=state.temperature,
                radiation_dose=state.radiation_dose,
                power_available=state.power_available + generated,
                power_consumed=state.power_consumed,
            )
        return result

    def name(self) -> str:
        return "power"


STRATEGIES["power"] = PowerModel
