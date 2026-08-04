"""
Engines layer (L2) — physics model static registry.

Static strategy registry — NOT dynamically discovered.

Extending: add your class + import + dict entry, or instantiate a
PhysicsModel directly and pass it to PhysicsOrchestrator without ever
touching this file.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.engines.physics.doppler import DopplerModel
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.power import PowerModel
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.engines.physics.thermal import ThermalModel
from skynetra.foundation.errors import PhysicsModelError

STRATEGIES: dict[str, type[PhysicsModel]] = {
    "thermal": ThermalModel,
    "radiation": RadiationModel,
    "power": PowerModel,
    "doppler": DopplerModel,
}


def build_physics_models(specs: list[dict[str, Any]]) -> list[PhysicsModel]:
    """specs = [{"name": "thermal", "config": {...}}, ...]"""
    out: list[PhysicsModel] = []
    for spec in specs:
        cls = STRATEGIES.get(spec["name"])
        if cls is None:
            raise PhysicsModelError(f"Unknown physics model '{spec['name']}'")
        out.append(cls(spec.get("config", {})))
    return out
