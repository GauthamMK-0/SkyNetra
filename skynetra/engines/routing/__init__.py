"""
Engines layer (L2) — routing subpackage.

May import from: itself, engines, domain, foundation.
"""

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
