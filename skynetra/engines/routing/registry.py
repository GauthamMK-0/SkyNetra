"""
Engines layer (L2) — static routing strategy registry.

Static strategy registry — NOT dynamically discovered.

Extending: add your class + import + dict entry, OR (for external
packages) import RoutingEngine directly and pass the class to
SkyNetraSimulation.from_layers(routing_engine=MyRouter(...)) without
ever touching this file.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.engines.routing.backpressure import BackPressureRouter
from skynetra.engines.routing.geographic import GeographicGreedyRouter
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.physics_compute_synergy import PhysicsComputeSynergyRouter
from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.engines.routing.thermal_energy import ThermalEnergyAwareRouter
from skynetra.foundation.errors import RoutingError

STRATEGIES: dict[str, type[RoutingEngine]] = {
    "shortest_path": ShortestPathRouter,
    "backpressure": BackPressureRouter,
    "geographic_greedy": GeographicGreedyRouter,
    "thermal_energy_aware": ThermalEnergyAwareRouter,
    "physics_compute_synergy": PhysicsComputeSynergyRouter,
}


def get_routing_engine(
    name: str, config: dict[str, Any] | None = None
) -> RoutingEngine:
    if name not in STRATEGIES:
        raise RoutingError(
            f"Unknown routing strategy '{name}'. "
            f"Available: {list(STRATEGIES)}"
        )
    return STRATEGIES[name](config)
