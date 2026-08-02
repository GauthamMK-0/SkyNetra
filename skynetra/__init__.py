"""
SkyNetra — simulation toolkit for compute-aware routing in space-based data center networks.

This package re-exports only the stable top-level API. The L3/L4 top-level
symbols (SkyNetraSimulation, FullConfig, SimulationResults) were previously
re-exported here eagerly; they are restored once the upper layers are
rebuilt against the current Layer 1 domain contract.
"""

from __future__ import annotations

__version__ = "0.1.0.dev0"

__all__ = [
    "__version__",
]
