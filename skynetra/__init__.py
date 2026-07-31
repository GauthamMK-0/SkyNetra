"""
SkyNetra — simulation toolkit for compute-aware routing in space-based data center networks.

This package re-exports only the stable top-level API.
"""

from __future__ import annotations

__version__ = "0.1.0.dev0"

from skynetra.interface.config.schema import FullConfig
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.results import SimulationResults

__all__ = [
    "__version__",
    "SkyNetraSimulation",
    "FullConfig",
    "SimulationResults",
]
