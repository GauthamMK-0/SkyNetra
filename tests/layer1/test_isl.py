from __future__ import annotations

from skynetra.domain.topology.isl import compute_isl_visibility, link_quality
from skynetra.foundation.types import Vector3


class TestComputeIslVisibility:
    def test_same_position(self):
        pos: Vector3 = (7000.0, 0.0, 0.0)
        assert compute_isl_visibility(pos, pos) is True

    def test_close_satellites_visible(self):
        a: Vector3 = (7000.0, 0.0, 0.0)
        b: Vector3 = (7000.0, 100.0, 0.0)
        assert compute_isl_visibility(a, b) is True

    def test_opposite_sides_of_earth_not_visible(self):
        a: Vector3 = (7000.0, 0.0, 0.0)
        b: Vector3 = (-7000.0, 0.0, 0.0)
        assert compute_isl_visibility(a, b) is False

    def test_low_altitude(self):
        a: Vector3 = (6400.0, 0.0, 0.0)
        b: Vector3 = (-6400.0, 0.0, 0.0)
        assert compute_isl_visibility(a, b) is False

    def test_zero_vector(self):
        assert compute_isl_visibility((0.0, 0.0, 0.0), (7000.0, 0.0, 0.0)) is False

    def test_custom_earth_radius(self):
        a: Vector3 = (2.0, 0.0, 0.0)
        b: Vector3 = (0.0, 2.0, 0.0)
        assert compute_isl_visibility(a, b, earth_radius_km=1.0) is True


class TestLinkQuality:
    def test_same_position_max_quality(self):
        pos: Vector3 = (7000.0, 0.0, 0.0)
        q = link_quality(pos, pos)
        assert q == 1.0

    def test_close_satellites_high_quality(self):
        a: Vector3 = (7000.0, 0.0, 0.0)
        b: Vector3 = (7000.0, 1.0, 0.0)
        q = link_quality(a, b)
        assert 0.9 < q <= 1.0

    def test_far_satellites_low_quality(self):
        a: Vector3 = (1e6, 0.0, 0.0)
        b: Vector3 = (-1e6, 0.0, 0.0)
        q = link_quality(a, b)
        assert 0.0 <= q < 0.5

    def test_quality_range(self):
        a: Vector3 = (1e7, 0.0, 0.0)
        b: Vector3 = (-1e7, 0.0, 0.0)
        q = link_quality(a, b)
        assert 0.0 <= q <= 1.0

    def test_snr_formula(self):
        a: Vector3 = (0.0, 0.0, 0.0)
        b: Vector3 = (1000.0, 0.0, 0.0)
        distance = 1000.0
        expected = 1.0 / (1.0 + distance * distance * 1e-12)
        assert abs(link_quality(a, b) - expected) < 1e-12
