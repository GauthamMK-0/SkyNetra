"""
Engines layer (L2) — routing, physics, workload algorithms.

Layer 2 defines the swappable ALGORITHM families that populate the
Layer 1 shapes: routing engines, physics models, workload generators.
Strategies are registered in static dicts (no dynamic discovery).

The workload sub-package is being rebuilt against the current Layer 1
domain contract; until it lands, this package re-exports only the
routing and physics sub-packages. The workload sub-package is
re-exported here again once rebuilt.

May import from: itself, domain (L1), foundation (L0).
"""

from __future__ import annotations

from skynetra.engines.physics.doppler import DopplerModel
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.power import PowerModel
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.engines.physics.registry import (
    STRATEGIES as PHYSICS_STRATEGIES,
)
from skynetra.engines.physics.registry import build_physics_models
from skynetra.engines.physics.thermal import ThermalModel
from skynetra.engines.routing.backpressure import BackPressureConfig, BackPressureRouter
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES, get_routing_engine
from skynetra.engines.routing.shortest_path import ShortestPathRouter

__all__ = [
    "RoutingEngine",
    "ShortestPathRouter",
    "BackPressureRouter",
    "BackPressureConfig",
    "STRATEGIES",
    "get_routing_engine",
    "PhysicsModel",
    "ThermalModel",
    "RadiationModel",
    "PowerModel",
    "DopplerModel",
    "PhysicsOrchestrator",
    "PHYSICS_STRATEGIES",
    "build_physics_models",
]
