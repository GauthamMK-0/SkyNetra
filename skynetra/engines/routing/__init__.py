"""
Engines layer (L2) — routing subpackage.

May import from: itself, engines, domain, foundation.
"""

from skynetra.engines.routing.backpressure import BackPressureConfig, BackPressureRouter
from skynetra.engines.routing.geographic import GeographicGreedyRouter
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.physics_compute_synergy import PhysicsComputeSynergyRouter
from skynetra.engines.routing.registry import STRATEGIES, get_routing_engine
from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.engines.routing.thermal_energy import ThermalEnergyAwareRouter

__all__ = [
    "RoutingEngine",
    "ShortestPathRouter",
    "BackPressureRouter",
    "BackPressureConfig",
    "GeographicGreedyRouter",
    "ThermalEnergyAwareRouter",
    "PhysicsComputeSynergyRouter",
    "STRATEGIES",
    "get_routing_engine",
]
