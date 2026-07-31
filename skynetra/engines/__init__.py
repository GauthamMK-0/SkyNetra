"""
Engines layer (L2) — routing, physics, workload algorithms.

May import from: itself, domain (L1), foundation (L0).
"""

from __future__ import annotations

from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import get_physics_model, list_physics_models
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import get_router, list_routers
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.registry import get_workload, list_workloads

__all__ = [
    "RoutingEngine",
    "get_router",
    "list_routers",
    "PhysicsModel",
    "get_physics_model",
    "list_physics_models",
    "WorkloadGenerator",
    "get_workload",
    "list_workloads",
]
