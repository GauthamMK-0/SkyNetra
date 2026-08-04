"""
Engines layer (L2) — routing, physics, workload algorithms.

Layer 2 defines the swappable ALGORITHM families that populate the
Layer 1 shapes: routing engines, physics models, workload generators.
Strategies are registered in static dicts (no dynamic discovery).

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
from skynetra.engines.workload.ai_training import AITrainingSyncWorkload
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.engines.workload.inference import InferenceQueryWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import (
    AITrainingSyncProfile,
    FederatedLearningProfile,
    ImageryDownlinkProfile,
    InferenceQueryProfile,
)
from skynetra.engines.workload.registry import (
    STRATEGIES as WORKLOAD_STRATEGIES,
)
from skynetra.engines.workload.registry import build_workloads

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
    "WorkloadGenerator",
    "AITrainingSyncProfile",
    "InferenceQueryProfile",
    "FederatedLearningProfile",
    "ImageryDownlinkProfile",
    "AITrainingSyncWorkload",
    "InferenceQueryWorkload",
    "FederatedLearningWorkload",
    "WORKLOAD_STRATEGIES",
    "build_workloads",
]
