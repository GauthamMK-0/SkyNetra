"""
Domain layer (L1) — orbit subpackage.

May import from: itself, domain, foundation.
"""

from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import PropagatorInterface

__all__ = [
    "ConstellationConfig",
    "PropagatorInterface",
]
