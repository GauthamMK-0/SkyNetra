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
    """Raised when an illegal cross-layer import is detected."""


class SimulationError(SkyNetraError):
    """Raised when the simulation encounters a runtime error."""


class PhysicsError(SkyNetraError):
    """Raised when a physics computation fails."""


class RoutingError(SkyNetraError):
    """Raised when a routing operation fails."""


class WorkloadError(SkyNetraError):
    """Raised when a workload generation step fails."""


class MetricsError(SkyNetraError):
    """Raised when a metrics collection step fails."""
