from __future__ import annotations

import math

import numpy as np
import pytest

from skynetra.foundation.math_utils import (
    EARTH_SIDEREAL_RATE_RAD_S,
    cartesian_to_spherical,
    circular_velocity_kms,
    free_space_path_loss_db,
    great_circle_distance,
    great_circle_distance_km,
    kepler_eccentric_anomaly,
    kepler_period_s,
    orbital_elements_to_eci,
    rotate_vector_z,
    rotation_matrix_x,
    rotation_matrix_y,
    rotation_matrix_z,
    sidereal_angle_rad,
    spherical_to_cartesian,
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


class TestKeplerPeriod:
    def test_550km_matches_known_period(self):
        period = kepler_period_s(550.0)
        assert abs(period - 5760.0) < 60.0

    def test_monotonic_with_altitude(self):
        low = kepler_period_s(300.0)
        high = kepler_period_s(1200.0)
        assert high > low

    def test_positive(self):
        assert kepler_period_s(0.0) > 0.0


class TestCircularVelocity:
    def test_value_positive(self):
        v = circular_velocity_kms(550.0)
        assert isinstance(v, float)
        assert 7.0 < v < 8.0

    def test_exact_value(self):
        v = circular_velocity_kms(550.0)
        assert abs(v - 7.588) < 0.01

    def test_decreases_with_altitude(self):
        assert circular_velocity_kms(1200.0) < circular_velocity_kms(300.0)


class TestOrbitalElementsToECI:
    def test_point_on_radius_sphere(self):
        alt = 550.0
        pos = orbital_elements_to_eci(53.0, 0.0, 90.0, alt)
        radius = math.sqrt(pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2)
        assert abs(radius - (6371.0 + alt)) < 1e-6

    def test_equatorial_raan_zero(self):
        pos = orbital_elements_to_eci(0.0, 0.0, 0.0, 550.0)
        r = 6371.0 + 550.0
        assert abs(pos[0] - r) < 1e-6
        assert abs(pos[1]) < 1e-6
        assert abs(pos[2]) < 1e-6

    def test_equatorial_raan_90(self):
        pos = orbital_elements_to_eci(0.0, 90.0, 0.0, 550.0)
        r = 6371.0 + 550.0
        assert abs(pos[0]) < 1e-6
        assert abs(pos[1] - r) < 1e-6
        assert abs(pos[2]) < 1e-6

    def test_polar_z_axis(self):
        pos = orbital_elements_to_eci(90.0, 0.0, 90.0, 550.0)
        r = 6371.0 + 550.0
        assert abs(pos[0]) < 1e-6
        assert abs(pos[1]) < 1e-6
        assert abs(pos[2] - r) < 1e-6


class TestGreatCircleDistanceKm:
    def test_same_point(self):
        p = (6371.0, 0.0, 0.0)
        assert abs(great_circle_distance_km(p, p)) < 1e-9

    def test_antipodal(self):
        a = (6371.0, 0.0, 0.0)
        b = (-6371.0, 0.0, 0.0)
        assert abs(great_circle_distance_km(a, b) - math.pi * 6371.0) < 1.0

    def test_quarter_turn(self):
        a = (6371.0, 0.0, 0.0)
        b = (0.0, 6371.0, 0.0)
        expected = 0.5 * math.pi * 6371.0
        assert abs(great_circle_distance_km(a, b) - expected) < 1.0


class TestFreeSpacePathLoss:
    def test_reference_1km_1ghz(self):
        db = free_space_path_loss_db(1.0, 1e9)
        assert abs(db - 92.45) < 0.01

    def test_increases_with_distance(self):
        assert free_space_path_loss_db(10.0, 1e9) > free_space_path_loss_db(1.0, 1e9)

    def test_increases_with_frequency(self):
        assert free_space_path_loss_db(1.0, 2e9) > free_space_path_loss_db(1.0, 1e9)


class TestEarthRotation:
    def test_rotate_vector_z_preserves_length_and_z(self):
        v = (1.0, 2.0, 3.0)
        rotated = rotate_vector_z(v, 0.7)
        assert rotated[2] == 3.0
        assert math.sqrt(sum(c * c for c in rotated)) == pytest.approx(
            math.sqrt(sum(c * c for c in v))
        )

    def test_rotate_vector_z_quarter_turn(self):
        v = rotate_vector_z((1.0, 0.0, 0.0), math.pi / 2)
        assert v[0] == pytest.approx(0.0, abs=1e-12)
        assert v[1] == pytest.approx(1.0, abs=1e-12)
        assert v[2] == pytest.approx(0.0, abs=1e-12)

    def test_rotate_vector_z_zero_angle_is_identity(self):
        v = (4.0, -5.0, 2.0)
        assert rotate_vector_z(v, 0.0) == v

    def test_sidereal_angle_full_sidereal_day(self):
        sidereal_day_s = 2.0 * math.pi / EARTH_SIDEREAL_RATE_RAD_S
        assert sidereal_angle_rad(sidereal_day_s) == pytest.approx(
            2.0 * math.pi, rel=1e-9
        )

    def test_sidereal_angle_solar_day_is_361_degrees(self):
        # A 24 h solar day is ~1.00274 sidereal days: the Earth sweeps
        # ~361 deg, not 360.
        assert sidereal_angle_rad(24 * 3600.0) == pytest.approx(6.30039, abs=1e-3)

    def test_sidereal_angle_one_hour(self):
        assert sidereal_angle_rad(3600.0) == pytest.approx(
            math.radians(15.041), rel=1e-3
        )
