"""
Domain layer (L1) — topology subpackage.

May import from: itself, domain, foundation.
"""

from skynetra.domain.topology.graph import build_topology_graph
from skynetra.domain.topology.isl import (
    compute_gsl_elevation_deg,
    compute_isl_link_quality,
)

__all__ = [
    "compute_isl_link_quality",
    "compute_gsl_elevation_deg",
    "build_topology_graph",
]
