"""
Domain layer (L1) — ISL visibility and link-quality math.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

import math

from skynetra.foundation.types import Vector3


def compute_isl_visibility(
    pos_a: Vector3, pos_b: Vector3, earth_radius_km: float = 6371.0
) -> bool:
    x1, y1, z1 = pos_a
    x2, y2, z2 = pos_b
    dot = x1 * x2 + y1 * y2 + z1 * z2
    norm_sq_a = x1 * x1 + y1 * y1 + z1 * z1
    norm_sq_b = x2 * x2 + y2 * y2 + z2 * z2
    if norm_sq_a <= 0 or norm_sq_b <= 0:
        return False
    cos_theta = dot / (math.sqrt(norm_sq_a) * math.sqrt(norm_sq_b))
    theta = math.acos(max(-1.0, min(1.0, cos_theta)))
    r_a = math.sqrt(norm_sq_a)
    r_b = math.sqrt(norm_sq_b)
    horizon_angle_a = math.asin(earth_radius_km / r_a) if r_a > earth_radius_km else 0.0
    horizon_angle_b = math.asin(earth_radius_km / r_b) if r_b > earth_radius_km else 0.0
    return theta < (math.pi - horizon_angle_a - horizon_angle_b)


def link_quality(
    pos_a: Vector3, pos_b: Vector3
) -> float:
    x1, y1, z1 = pos_a
    x2, y2, z2 = pos_b
    distance = math.sqrt(
        (x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2
    )
    snr = 1.0 / (1.0 + distance * distance * 1e-12)
    return max(0.0, min(1.0, snr))
