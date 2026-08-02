from __future__ import annotations

import pytest

from skynetra.domain.topology.isl import (
    DEFAULT_LINK_QUALITY,
    SPEED_OF_LIGHT_KM_S,
    compute_gsl_elevation_deg,
    compute_isl_link_quality,
)
from skynetra.foundation.types import Vector3

POS_A: Vector3 = (7000.0, 0.0, 0.0)
POS_B: Vector3 = (7000.0, 100.0, 0.0)


def _expected_delay_ms(distance_km: float) -> float:
    return distance_km * 1000.0 / SPEED_OF_LIGHT_KM_S


class TestComputeIslLinkQuality:
    def test_nominal_defaults_without_overrides(self):
        quality = compute_isl_link_quality(POS_A, POS_B, distance_km=100.0)
        assert quality["capacity"] == 10.0
        assert quality["propagation_delay_ms"] == pytest.approx(
            _expected_delay_ms(100.0)
        )
        assert quality["thermal_noise_factor"] == 1.0
        assert quality["radiation_bit_error_rate"] == 0.0
        assert quality["effective_capacity_fraction"] == 1.0
        assert quality["doppler_shift_hz"] == 0.0

    def test_full_schema_present(self):
        quality = compute_isl_link_quality(POS_A, POS_B, distance_km=100.0)
        assert set(quality.keys()) == set(DEFAULT_LINK_QUALITY.keys())

    def test_zero_distance(self):
        quality = compute_isl_link_quality(POS_A, POS_B, distance_km=0.0)
        assert quality["propagation_delay_ms"] == 0.0

    def test_distance_scales_delay(self):
        quality = compute_isl_link_quality(POS_A, POS_B, distance_km=2000.0)
        assert quality["propagation_delay_ms"] == pytest.approx(
            _expected_delay_ms(2000.0)
        )

    def test_none_overrides_returns_defaults(self):
        quality = compute_isl_link_quality(POS_A, POS_B, distance_km=100.0, physics_overrides=None)
        assert quality["doppler_shift_hz"] == 0.0

    def test_physics_overrides_merged(self):
        quality = compute_isl_link_quality(
            POS_A, POS_B, distance_km=100.0, physics_overrides={"doppler_shift_hz": 500.0}
        )
        assert quality["doppler_shift_hz"] == 500.0
        assert quality["effective_capacity_fraction"] == 1.0
        assert quality["propagation_delay_ms"] == pytest.approx(_expected_delay_ms(100.0))

    def test_partial_overrides_keep_other_defaults(self):
        quality = compute_isl_link_quality(
            POS_A,
            POS_B,
            distance_km=100.0,
            physics_overrides={"effective_capacity_fraction": 0.4},
        )
        assert quality["effective_capacity_fraction"] == 0.4
        assert quality["thermal_noise_factor"] == 1.0
        assert quality["radiation_bit_error_rate"] == 0.0

    def test_positions_not_used_for_distance(self):
        quality = compute_isl_link_quality(POS_A, POS_B, distance_km=50.0)
        assert quality["propagation_delay_ms"] == pytest.approx(_expected_delay_ms(50.0))


class TestComputeGslElevationDeg:
    def test_satellite_overhead(self):
        assert compute_gsl_elevation_deg((6921.0, 0.0, 0.0), (6371.0, 0.0, 0.0)) == pytest.approx(
            90.0
        )

    def test_satellite_at_horizon(self):
        elevation = compute_gsl_elevation_deg((7000.0, 0.0, 0.0), (7000.0, 100.0, 0.0))
        assert elevation == pytest.approx(0.0, abs=1.0)

    def test_opposite_side_is_below_horizon(self):
        elevation = compute_gsl_elevation_deg((-6921.0, 0.0, 0.0), (6371.0, 0.0, 0.0))
        assert elevation < 0.0

    def test_degenerate_gs_position(self):
        assert compute_gsl_elevation_deg((6921.0, 0.0, 0.0), (0.0, 0.0, 0.0)) == -90.0
