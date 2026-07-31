"""
Engines layer (L2) — static physics model registry.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict, Type

from skynetra.engines.physics.interface import PhysicsModel

STRATEGIES: Dict[str, Type[PhysicsModel]] = {}


def get_physics_model(name: str, **kwargs: object) -> PhysicsModel:
    cls = STRATEGIES.get(name)
    if cls is None:
        raise KeyError(f"Unknown physics model: {name}")
    return cls(**kwargs)


def list_physics_models() -> list[str]:
    return list(STRATEGIES.keys())
