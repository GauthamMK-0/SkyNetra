"""
Foundation layer (L0) — pure utilities, no internal SkyNetra dependencies.

May import from: itself only.
"""

from skynetra.foundation.errors import (
    ConfigError,
    LayerViolationError,
    MetricsError,
    PhysicsModelError,
    RoutingError,
    SimulationError,
    SkyNetraError,
    TopologyError,
    WorkloadError,
)
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.logging_setup import configure_logging, get_logger
from skynetra.foundation.math_utils import (
    cartesian_to_spherical,
    circular_velocity_kms,
    free_space_path_loss_db,
    great_circle_distance,
    great_circle_distance_km,
    kepler_eccentric_anomaly,
    kepler_period_s,
    orbital_elements_to_eci,
    rotation_matrix_x,
    rotation_matrix_y,
    rotation_matrix_z,
    spherical_to_cartesian,
)
from skynetra.foundation.time_utils import (
    is_in_eclipse,
    sim_time_to_orbital_phase,
    sim_to_wallclock,
    wallclock_to_sim,
)
from skynetra.foundation.types import LinkId, NodeId, TimeSeconds, Vector3

__all__ = [
    "NodeId",
    "LinkId",
    "Vector3",
    "TimeSeconds",
    "SkyNetraError",
    "ConfigError",
    "LayerViolationError",
    "TopologyError",
    "RoutingError",
    "PhysicsModelError",
    "SimulationError",
    "WorkloadError",
    "MetricsError",
    "EventBus",
    "configure_logging",
    "get_logger",
    "kepler_eccentric_anomaly",
    "kepler_period_s",
    "circular_velocity_kms",
    "orbital_elements_to_eci",
    "great_circle_distance_km",
    "free_space_path_loss_db",
    "rotation_matrix_x",
    "rotation_matrix_y",
    "rotation_matrix_z",
    "spherical_to_cartesian",
    "cartesian_to_spherical",
    "great_circle_distance",
    "sim_to_wallclock",
    "wallclock_to_sim",
    "sim_time_to_orbital_phase",
    "is_in_eclipse",
]
