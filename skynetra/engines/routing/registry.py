"""
Engines layer (L2) — static routing strategy registry.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict, Type

from skynetra.engines.routing.interface import RoutingEngine

STRATEGIES: Dict[str, Type[RoutingEngine]] = {}


def get_router(name: str, **kwargs: object) -> RoutingEngine:
    cls = STRATEGIES.get(name)
    if cls is None:
        raise KeyError(f"Unknown routing strategy: {name}")
    return cls(**kwargs)


def list_routers() -> list[str]:
    return list(STRATEGIES.keys())
