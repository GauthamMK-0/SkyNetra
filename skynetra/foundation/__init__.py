"""
Foundation layer (L0) — pure utilities, no internal SkyNetra dependencies.

May import from: itself only.
"""

from skynetra.foundation.errors import ConfigError, LayerViolationError, SkyNetraError
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.logging_setup import configure_logging
from skynetra.foundation.math_utils import (
    cartesian_to_spherical,
    great_circle_distance,
    kepler_eccentric_anomaly,
    rotation_matrix_x,
    rotation_matrix_y,
    rotation_matrix_z,
    spherical_to_cartesian,
)
from skynetra.foundation.time_utils import sim_to_wallclock, wallclock_to_sim
from skynetra.foundation.types import LinkId, NodeId, TimeSeconds, Vector3

__all__ = [
    "NodeId",
    "LinkId",
    "Vector3",
    "TimeSeconds",
    "SkyNetraError",
    "ConfigError",
    "LayerViolationError",
    "EventBus",
    "configure_logging",
    "kepler_eccentric_anomaly",
    "rotation_matrix_x",
    "rotation_matrix_y",
    "rotation_matrix_z",
    "spherical_to_cartesian",
    "cartesian_to_spherical",
    "great_circle_distance",
    "sim_to_wallclock",
    "wallclock_to_sim",
]
