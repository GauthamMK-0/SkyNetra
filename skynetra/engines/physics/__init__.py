"""
Engines layer (L2) — physics subpackage.

May import from: itself, engines, domain, foundation.
"""

from skynetra.engines.physics.doppler import DopplerModel
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.power import PowerModel
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.engines.physics.registry import STRATEGIES, get_physics_model, list_physics_models
from skynetra.engines.physics.thermal import ThermalModel

__all__ = [
    "PhysicsModel",
    "ThermalModel",
    "RadiationModel",
    "PowerModel",
    "DopplerModel",
    "PhysicsOrchestrator",
    "STRATEGIES",
    "get_physics_model",
    "list_physics_models",
]
