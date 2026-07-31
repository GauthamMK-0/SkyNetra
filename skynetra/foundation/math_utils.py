"""
Foundation layer (L0) — Kepler math, rotation matrices, geometry helpers.

May import from: itself only.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

Vector3 = Tuple[float, float, float]


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


def rotation_matrix_x(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rotation_matrix_y(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def rotation_matrix_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


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
    lat1: float, lon1: float, lat2: float, lon2: float, R: float = 6371.0
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
