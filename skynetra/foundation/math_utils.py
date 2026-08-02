"""
Foundation layer (L0) — Kepler math, rotation matrices, geometry helpers.

May import from: itself only.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np
from numpy.typing import NDArray

Vector3 = tuple[float, float, float]

EARTH_RADIUS_KM = 6371.0
EARTH_MU_KM3_S2 = 3.986004418e5


def kepler_eccentric_anomaly(
    mean_anomaly: float, eccentricity: float, tol: float = 1e-12, max_iter: int = 100
) -> float:
    E = mean_anomaly
    for _ in range(max_iter):
        dE = (mean_anomaly - E + eccentricity * math.sin(E)) / (
            1.0 - eccentricity * math.cos(E)
        )
        E += dE
        if abs(dE) < tol:
            break
    return E


def kepler_period_s(altitude_km: float) -> float:
    """Orbital period for a circular orbit at `altitude_km`, in seconds."""
    radius_km = EARTH_RADIUS_KM + altitude_km
    return 2.0 * math.pi * math.sqrt(radius_km**3 / EARTH_MU_KM3_S2)


def circular_velocity_kms(altitude_km: float) -> float:
    """Circular orbital speed at `altitude_km`, in km/s."""
    radius_km = EARTH_RADIUS_KM + altitude_km
    return math.sqrt(EARTH_MU_KM3_S2 / radius_km)


def orbital_elements_to_eci(
    inc_deg: float,
    raan_deg: float,
    mean_anomaly_deg: float,
    altitude_km: float,
) -> Vector3:
    """ECI position for a circular orbit from Keplerian elements, in km.

    Assumes zero argument of periapsis; mean anomaly equals the in-plane
    angle (circular orbit). Applies the rotation order Rz(Omega) * Rx(inc).
    """
    radius_km = EARTH_RADIUS_KM + altitude_km
    inc = math.radians(inc_deg)
    raan = math.radians(raan_deg)
    u = math.radians(mean_anomaly_deg)

    cos_inc, sin_inc = math.cos(inc), math.sin(inc)
    cos_raan, sin_raan = math.cos(raan), math.sin(raan)
    cos_u, sin_u = math.cos(u), math.sin(u)

    x = radius_km * (cos_raan * cos_u - sin_raan * sin_u * cos_inc)
    y = radius_km * (sin_raan * cos_u + cos_raan * sin_u * cos_inc)
    z = radius_km * (sin_u * sin_inc)
    return (x, y, z)


def great_circle_distance_km(pos_a: Vector3, pos_b: Vector3) -> float:
    """Great-circle distance in km between two points on a common sphere."""
    ax, ay, az = pos_a
    bx, by, bz = pos_b
    norm_a = math.sqrt(ax * ax + ay * ay + az * az)
    norm_b = math.sqrt(bx * bx + by * by + bz * bz)
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    cos_theta = (ax * bx + ay * by + az * bz) / (norm_a * norm_b)
    theta = math.acos(max(-1.0, min(1.0, cos_theta)))
    return theta * EARTH_RADIUS_KM


def free_space_path_loss_db(distance_km: float, freq_hz: float) -> float:
    """Free-space path loss in dB using distance and carrier frequency."""
    distance_m = distance_km * 1000.0
    return 20.0 * math.log10(distance_m) + 20.0 * math.log10(freq_hz) - 147.55


def rotation_matrix_z(angle_rad: float) -> NDArray[np.float64]:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rotation_matrix_x(angle_rad: float) -> NDArray[np.float64]:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rotation_matrix_y(angle_rad: float) -> NDArray[np.float64]:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def spherical_to_cartesian(
    r: float, theta: float, phi: float
) -> Vector3:
    x = r * math.sin(theta) * math.cos(phi)
    y = r * math.sin(theta) * math.sin(phi)
    z = r * math.cos(theta)
    return (x, y, z)


def cartesian_to_spherical(
    x: float, y: float, z: float
) -> Tuple[float, float, float]:
    r = math.sqrt(x * x + y * y + z * z)
    theta = math.acos(z / r) if r > 0 else 0.0
    phi = math.atan2(y, x)
    return (r, theta, phi)


def great_circle_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, R: float = EARTH_RADIUS_KM
) -> float:
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
