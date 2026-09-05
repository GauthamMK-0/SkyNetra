"""
Domain layer (L1) — inter-satellite link (ISL) quality and GSL geometry.

`compute_isl_link_quality` is a pure function: given two satellite ECI
positions and a distance, it returns the full link-quality attribute
schema as a plain dict. The schema slots (capacity, propagation delay,
thermal noise, radiation bit-error rate, effective capacity fraction,
Doppler shift) are owned by Layer 1; only Layer 2 physics engines
populate non-default values.

`physics_overrides` is an OPTIONAL plain dict passed in by Layer 2 physics
engines. Layer 1 never imports `skynetra.engines.physics` — Layer 2
computes numbers and passes them DOWN as plain dicts into these Layer 1
pure functions. This keeps the dependency direction correct.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

import math
from typing import Any

from skynetra.foundation.types import Vector3

SPEED_OF_LIGHT_KM_S = 299792.458

DEFAULT_LINK_QUALITY: dict[str, float] = {
    "capacity": 10.0,  # Gbps
    "propagation_delay_ms": 0.0,
    "thermal_noise_factor": 1.0,
    "radiation_bit_error_rate": 0.0,
    "effective_capacity_fraction": 1.0,
    "doppler_shift_hz": 0.0,
}


def compute_isl_link_quality(
    sat_a_pos: Vector3,
    sat_b_pos: Vector3,
    distance_km: float,
    physics_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Link-quality attribute dict for the A->B link at `distance_km`.

    Returns the full schema with defaults, then merges any
    `physics_overrides` supplied by a Layer 2 physics engine on top.
    `sat_a_pos`/`sat_b_pos` are retained in the caller's frame (ECI, km)
    and are used only for derived geometry; the propagation delay is
    computed from `distance_km` and the speed of light.
    """
    quality: dict[str, Any] = dict(DEFAULT_LINK_QUALITY)
    quality["propagation_delay_ms"] = distance_km * 1000.0 / SPEED_OF_LIGHT_KM_S
    if physics_overrides:
        quality.update(physics_overrides)
    return quality


def compute_gsl_elevation_deg(sat_pos: Vector3, gs_pos: Vector3) -> float:
    """Elevation angle (degrees) of `sat_pos` above the horizon at `gs_pos`.

    Both positions must be in the same Cartesian frame (ECI, km). The
    local 'up' at the ground station is the station's own radial vector;
    the elevation is the angle between the satellite direction and that
    local horizon plane. Returns a value in [-90, 90].
    """
    sx, sy, sz = sat_pos
    gx, gy, gz = gs_pos
    gs_norm = math.sqrt(gx * gx + gy * gy + gz * gz)
    if gs_norm <= 0.0:
        return -90.0
    up_x, up_y, up_z = gx / gs_norm, gy / gs_norm, gz / gs_norm
    dx, dy, dz = sx - gx, sy - gy, sz - gz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist <= 0.0:
        return 90.0
    sin_elev = (dx * up_x + dy * up_y + dz * up_z) / dist
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_elev))))
