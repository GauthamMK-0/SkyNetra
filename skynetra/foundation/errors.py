"""
Foundation layer (L0) — SkyNetra error hierarchy.

May import from: itself only.
"""

from __future__ import annotations


class SkyNetraError(Exception):
    """Base exception for all SkyNetra errors."""


class ConfigError(SkyNetraError):
    """Raised when a configuration is invalid or incomplete."""


class LayerViolationError(SkyNetraError):
    """Raised by test tooling if a runtime check detects an upward import.

    Defensive enforcement only; the primary enforcement is import-linter in CI.
    """


class TopologyError(SkyNetraError):
    """Raised when a topology/graph operation fails."""


class RoutingError(SkyNetraError):
    """Raised when a routing operation fails."""


class PhysicsModelError(SkyNetraError):
    """Raised when a physics computation fails."""


class SimulationError(SkyNetraError):
    """Raised when the simulation encounters a runtime error."""


class WorkloadError(SkyNetraError):
    """Raised when a workload generation step fails."""


class MetricsError(SkyNetraError):
    """Raised when a metrics collection step fails."""


__all__ = [
    "SkyNetraError",
    "ConfigError",
    "LayerViolationError",
    "TopologyError",
    "RoutingError",
    "PhysicsModelError",
    "SimulationError",
    "WorkloadError",
    "MetricsError",
]
