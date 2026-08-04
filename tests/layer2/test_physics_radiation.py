from __future__ import annotations

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId

CONSTELLATION = ConstellationConfig(
    n_planes=3, sats_per_plane=4, altitude_km=550.0, inclination_deg=53.0
)


def _node() -> RelayNode:
    return RelayNode(NodeId("sat-1"))


def _tick(
    model: RadiationModel,
    node: Node,
    time_s: float,
    dt_s: float,
) -> dict[str, float]:
    return model.compute_node_physics(
        node.node_id, node, None, time_s, dt_s, CONSTELLATION
    )


class TestRadiationModel:
    def test_is_physics_model(self):
        assert isinstance(RadiationModel(), PhysicsModel)

    def test_defaults_to_disabled(self):
        assert RadiationModel().enabled is False

    def test_disabled_returns_unchanged_state(self):
        node = _node()
        result = _tick(RadiationModel(), node, 100.0, 10.0)
        assert result == dict(node.physics_state)

    def test_dose_accumulates(self):
        model = RadiationModel({"enabled": True, "background_dose_rate_rad_s": 0.01})
        node = _node()
        delta = _tick(model, node, 0.0, 10.0)
        assert delta["radiation_dose_rad"] == pytest.approx(0.1)

    def test_dose_accumulates_over_multiple_ticks(self):
        model = RadiationModel({"enabled": True, "background_dose_rate_rad_s": 0.01})
        node = _node()
        for i in range(5):
            node.update_physics(_tick(model, node, float(i), 1.0))
        assert node.physics_state["radiation_dose_rad"] == pytest.approx(0.05)

    def test_custom_dose_rate(self):
        model = RadiationModel({"enabled": True, "background_dose_rate_rad_s": 0.5})
        node = _node()
        delta = _tick(model, node, 0.0, 2.0)
        assert delta["radiation_dose_rad"] == pytest.approx(1.0)

    def test_saa_window_boosts_rate(self):
        model = RadiationModel(
            {
                "enabled": True,
                "background_dose_rate_rad_s": 1.0,
                "saa_boost_factor": 10.0,
                "saa_phase_start_f": 0.0,
                "saa_phase_width_f": 0.1,
            }
        )
        node = _node()
        period = 2.0 * 3.141592653589793 * ((6371.0 + 550.0) ** 3 / 3.986004418e5) ** 0.5
        in_window = _tick(model, node, 0.0, 1.0)["radiation_dose_rad"]
        outside = _tick(model, node, 0.2 * period, 1.0)["radiation_dose_rad"]
        assert in_window == pytest.approx(10.0)
        assert outside == pytest.approx(1.0)

    def test_solar_event_window_boosts_rate(self):
        model = RadiationModel(
            {
                "enabled": True,
                "background_dose_rate_rad_s": 1.0,
                "solar_event_period_s": 10.0,
                "solar_event_duration_s": 5.0,
                "solar_event_phase_shift_f": 0.0,
                "solar_event_dose_multiplier": 100.0,
            }
        )
        node = _node()
        during_event = _tick(model, node, 1.0, 1.0)["radiation_dose_rad"]
        between_events = _tick(model, node, 7.0, 1.0)["radiation_dose_rad"]
        assert during_event == pytest.approx(100.0)
        assert between_events == pytest.approx(1.0)

    def test_link_bit_error_rate(self):
        model = RadiationModel(
            {"enabled": True, "background_dose_rate_rad_s": 0.01, "ber_scale": 1e-3}
        )
        link = model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        assert link["radiation_bit_error_rate"] == pytest.approx(1e-5)

    def test_disabled_link_physics_empty(self):
        assert RadiationModel().compute_link_physics(
            NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0
        ) == {}

    def test_get_summary(self):
        summary = RadiationModel({"enabled": True}).get_summary()
        assert summary["enabled"] is True
        assert "latchup_threshold_rad" in summary

    def test_registered(self):
        assert "radiation" in STRATEGIES
        assert STRATEGIES["radiation"] is RadiationModel


class TestRadiationLatchup:
    def test_threshold_sets_fault_and_node_goes_down(self):
        model = RadiationModel(
            {
                "enabled": True,
                "background_dose_rate_rad_s": 1.0,
                "latchup_threshold_rad": 1000.0,
            }
        )
        node = _node()
        for i in range(1000):
            node.update_physics(_tick(model, node, float(i), 1.0))
        assert node.physics_state["radiation_dose_rad"] == pytest.approx(1000.0)
        assert node.physics_state["fault_probability"] == 1.0
        assert node.is_operational() is False

    def test_below_threshold_no_fault(self):
        model = RadiationModel(
            {
                "enabled": True,
                "background_dose_rate_rad_s": 1.0,
                "latchup_threshold_rad": 1000.0,
            }
        )
        node = _node()
        delta = _tick(model, node, 0.0, 999.0)
        assert "fault_probability" not in delta
        node.update_physics(delta)
        assert node.is_operational() is True
