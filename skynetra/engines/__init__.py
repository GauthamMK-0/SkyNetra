"""
Engines layer (L2) — routing, physics, workload algorithms.

Layer 2 defines the swappable ALGORITHM families that populate the
Layer 1 shapes: routing engines, physics models, workload generators.
Strategies are registered in static dicts (no dynamic discovery).

The physics and workload sub-packages are being rebuilt against the
current Layer 1 domain contract; until they land, this package
re-exports only the routing sub-package. The other sub-packages are
re-exported here again as each one is rebuilt.

May import from: itself, domain (L1), foundation (L0).
"""

from __future__ import annotations

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
]
