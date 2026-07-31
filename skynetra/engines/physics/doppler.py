"""
Engines layer (L2) — doppler shift model.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId


class DopplerModel(PhysicsModel):
    def __init__(self, carrier_freq_hz: float = 2.4e9) -> None:
        self._freq = carrier_freq_hz

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        return {nid: state for nid, state in states.items()}

    def name(self) -> str:
        return "doppler"


STRATEGIES["doppler"] = DopplerModel
