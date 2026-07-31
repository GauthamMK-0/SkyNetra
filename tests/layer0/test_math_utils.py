from __future__ import annotations

import math

import numpy as np
import pytest

from skynetra.foundation.math_utils import (
    kepler_eccentric_anomaly,
    rotation_matrix_x,
    rotation_matrix_y,
    rotation_matrix_z,
    spherical_to_cartesian,
    cartesian_to_spherical,
    great_circle_distance,
)


class TestKepler:
    def test_circular_orbit(self):
        E = kepler_eccentric_anomaly(0.5, 0.0)
        assert abs(E - 0.5) < 1e-12

    def test_eccentric_orbit(self):
        E = kepler_eccentric_anomaly(1.0, 0.5)
        assert isinstance(E, float)
        assert 0 < E < 2 * math.pi

    def test_convergence(self):
        E = kepler_eccentric_anomaly(3.0, 0.9, tol=1e-10)
        assert not math.isnan(E)

    def test_zero_mean_anomaly(self):
        E = kepler_eccentric_anomaly(0.0, 0.5)
        assert abs(E) < 1e-12


class TestRotationMatrices:
    def test_rotation_matrix_x_identity(self):
        R = rotation_matrix_x(0.0)
        np.testing.assert_array_almost_equal(R, np.eye(3))

    def test_rotation_matrix_x_90(self):
        R = rotation_matrix_x(math.pi / 2)
        expected = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
        np.testing.assert_array_almost_equal(R, expected)

    def test_rotation_matrix_y_identity(self):
        R = rotation_matrix_y(0.0)
        np.testing.assert_array_almost_equal(R, np.eye(3))

    def test_rotation_matrix_z_identity(self):
        R = rotation_matrix_z(0.0)
        np.testing.assert_array_almost_equal(R, np.eye(3))

    def test_rotation_matrix_z_90(self):
        R = rotation_matrix_z(math.pi / 2)
        expected = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
        np.testing.assert_array_almost_equal(R, expected)

    def test_orthogonality(self):
        for fn in (rotation_matrix_x, rotation_matrix_y, rotation_matrix_z):
            R = fn(0.7)
            np.testing.assert_array_almost_equal(R @ R.T, np.eye(3))


class TestCoordinateTransforms:
    def test_spherical_to_cartesian_equator(self):
        x, y, z = spherical_to_cartesian(1.0, math.pi / 2, 0.0)
        assert abs(x - 1.0) < 1e-12
        assert abs(y) < 1e-12
        assert abs(z) < 1e-12

    def test_cartesian_to_spherical_identity(self):
        orig = (3.0, 4.0, 5.0)
        r, theta, phi = cartesian_to_spherical(*orig)
        x, y, z = spherical_to_cartesian(r, theta, phi)
        np.testing.assert_array_almost_equal((x, y, z), orig)

    def test_cartesian_to_spherical_origin(self):
        r, theta, phi = cartesian_to_spherical(0.0, 0.0, 0.0)
        assert r == 0.0
        assert theta == 0.0
        assert phi == 0.0

    def test_spherical_to_cartesian_north_pole(self):
        x, y, z = spherical_to_cartesian(1.0, 0.0, 0.0)
        assert abs(x) < 1e-12
        assert abs(y) < 1e-12
        assert abs(z - 1.0) < 1e-12


class TestGreatCircleDistance:
    def test_same_point(self):
        d = great_circle_distance(0.0, 0.0, 0.0, 0.0)
        assert abs(d) < 1e-12

    def test_antipodal(self):
        d = great_circle_distance(0.0, 0.0, 0.0, 180.0)
        assert abs(d - math.pi * 6371.0) < 1.0

    def test_quarter_equator(self):
        d = great_circle_distance(0.0, 0.0, 0.0, 90.0)
        expected = 0.5 * math.pi * 6371.0
        assert abs(d - expected) < 1.0

    def test_custom_radius(self):
        d = great_circle_distance(0.0, 0.0, 0.0, 90.0, R=1.0)
        assert abs(d - math.pi / 2) < 1e-6

    def test_known_cities(self):
        d = great_circle_distance(52.52, 13.405, 48.8566, 2.3522)
        assert 800 < d < 1000
