from __future__ import annotations

import math

import pytest

from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import (
    PropagatorInterface,
    ReferenceCircularPropagator,
)
from skynetra.foundation.math_utils import EARTH_RADIUS_KM, kepler_period_s, orbital_elements_to_eci
from skynetra.foundation.types import NodeId


def _constellation(
    n_planes: int = 3,
    sats_per_plane: int = 3,
    altitude_km: float = 550.0,
    inclination_deg: float = 53.0,
    phase_offset_f: int = 1,
    raan_spread_deg: float = 360.0,
) -> ConstellationConfig:
    return ConstellationConfig(
        n_planes=n_planes,
        sats_per_plane=sats_per_plane,
        altitude_km=altitude_km,
        inclination_deg=inclination_deg,
        phase_offset_f=phase_offset_f,
        raan_spread_deg=raan_spread_deg,
    )


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        PropagatorInterface()  # type: ignore[abstract]


class TestOrbitalPeriod:
    def test_matches_kepler_period_s(self):
        assert ReferenceCircularPropagator().get_orbital_period_s(550.0) == pytest.approx(
            kepler_period_s(550.0)
        )

    def test_leo_period_sanity(self):
        period = ReferenceCircularPropagator().get_orbital_period_s(550.0)
        assert 5400.0 < period < 6000.0  # ~95 min LEO

    def test_period_grows_with_altitude(self):
        propagator = ReferenceCircularPropagator()
        assert propagator.get_orbital_period_s(1500.0) > propagator.get_orbital_period_s(550.0)


class TestReferenceCircularPropagatorSatIds:
    def test_id_count_and_order(self):
        propagator = ReferenceCircularPropagator()
        sat_ids = propagator.get_sat_ids(_constellation())
        assert len(sat_ids) == 9
        assert sat_ids == [
            NodeId("sat-0-0"),
            NodeId("sat-0-1"),
            NodeId("sat-0-2"),
            NodeId("sat-1-0"),
            NodeId("sat-1-1"),
            NodeId("sat-1-2"),
            NodeId("sat-2-0"),
            NodeId("sat-2-1"),
            NodeId("sat-2-2"),
        ]

    def test_total_matches_config(self):
        config = _constellation(n_planes=4, sats_per_plane=6)
        propagator = ReferenceCircularPropagator()
        assert len(propagator.get_sat_ids(config)) == config.total_satellites

    def test_positions_keyed_by_all_sat_ids(self):
        config = _constellation()
        propagator = ReferenceCircularPropagator()
        positions = propagator.get_positions(0.0, config)
        assert sorted(positions.keys()) == sorted(propagator.get_sat_ids(config))


class TestReferenceCircularPropagatorEciGeometry:
    def test_positions_lie_on_orbit_sphere(self):
        config = _constellation()
        radius_km = EARTH_RADIUS_KM + config.altitude_km
        propagator = ReferenceCircularPropagator()
        for position in propagator.get_positions(0.0, config).values():
            norm = math.sqrt(sum(component**2 for component in position))
            assert norm == pytest.approx(radius_km, rel=1e-9)

    def test_initial_position_matches_orbital_elements(self):
        config = _constellation()
        propagator = ReferenceCircularPropagator()
        expected = orbital_elements_to_eci(
            inc_deg=53.0, raan_deg=0.0, mean_anomaly_deg=0.0, altitude_km=550.0
        )
        assert propagator.get_positions(0.0, config)[NodeId("sat-0-0")] == pytest.approx(
            expected
        )

    def test_raan_spread_positions_plane_1(self):
        config = _constellation()
        propagator = ReferenceCircularPropagator()
        expected = orbital_elements_to_eci(
            inc_deg=53.0, raan_deg=120.0, mean_anomaly_deg=40.0, altitude_km=550.0
        )
        assert propagator.get_positions(0.0, config)[NodeId("sat-1-0")] == pytest.approx(
            expected
        )

    def test_raan_spread_param(self):
        config = _constellation(n_planes=2, sats_per_plane=2, raan_spread_deg=180.0)
        propagator = ReferenceCircularPropagator()
        expected = orbital_elements_to_eci(
            inc_deg=53.0, raan_deg=90.0, mean_anomaly_deg=90.0, altitude_km=550.0
        )
        assert propagator.get_positions(0.0, config)[NodeId("sat-1-0")] == pytest.approx(
            expected
        )

    def test_phase_offset_shifts_plane_1(self):
        config = _constellation()
        propagator = ReferenceCircularPropagator()
        with_offset = propagator.get_positions(0.0, config)[NodeId("sat-1-0")]
        no_offset_config = _constellation(phase_offset_f=0)
        without_offset = propagator.get_positions(0.0, no_offset_config)[
            NodeId("sat-1-0")
        ]
        assert with_offset != pytest.approx(without_offset)


class TestReferenceCircularPropagatorOrbitMath:
    def test_period_symmetry(self):
        config = _constellation()
        propagator = ReferenceCircularPropagator()
        period = propagator.get_orbital_period_s(config.altitude_km)
        t0 = propagator.get_positions(0.0, config)
        t1 = propagator.get_positions(period, config)
        for sat_id in propagator.get_sat_ids(config):
            assert t1[sat_id] == pytest.approx(t0[sat_id], rel=1e-9, abs=1e-8)

    def test_mean_anomaly_advances_with_mean_motion(self):
        config = _constellation()
        propagator = ReferenceCircularPropagator()
        period = propagator.get_orbital_period_s(config.altitude_km)
        at_quarter_period = propagator.get_positions(period / 4.0, config)[
            NodeId("sat-0-0")
        ]
        expected = orbital_elements_to_eci(
            inc_deg=53.0, raan_deg=0.0, mean_anomaly_deg=90.0, altitude_km=550.0
        )
        assert at_quarter_period == pytest.approx(expected, rel=1e-9)
