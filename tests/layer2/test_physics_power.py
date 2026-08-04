from __future__ import annotations

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.power import PowerModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId

CONSTELLATION = ConstellationConfig(
    n_planes=3, sats_per_plane=4, altitude_km=550.0, inclination_deg=53.0
)

SOLAR_FLUX_W_M2 = 1361.0


def _node() -> RelayNode:
    return RelayNode(NodeId("sat-1"))


def _tick(
    model: PowerModel,
    node: Node,
    time_s: float,
    dt_s: float,
) -> dict[str, float]:
    return model.compute_node_physics(
        node.node_id, node, None, time_s, dt_s, CONSTELLATION
    )


class TestPowerModel:
    def test_is_physics_model(self):
        assert isinstance(PowerModel(), PhysicsModel)

    def test_defaults_to_disabled(self):
        assert PowerModel().enabled is False

    def test_disabled_returns_unchanged_state(self):
        node = _node()
        result = _tick(PowerModel(), node, 100.0, 1.0)
        assert result == dict(node.physics_state)

    def test_sunlight_generates_power(self):
        model = PowerModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "solar_panel_area_m2": 10.0,
                "solar_efficiency": 0.3,
            }
        )
        node = _node()
        delta = _tick(model, node, 0.0, 1.0)
        expected = SOLAR_FLUX_W_M2 * 10.0 * 0.3
        assert delta["power_available_w"] == pytest.approx(expected)

    def test_sunlight_charges_battery(self):
        model = PowerModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "solar_panel_area_m2": 10.0,
                "solar_efficiency": 0.3,
                "battery_capacity_wh": 50000.0,
                "battery_charge_wh": 0.0,
                "charge_efficiency": 0.9,
            }
        )
        node = _node()
        delta = _tick(model, node, 0.0, 1.0)
        assert delta["battery_charge_wh"] == pytest.approx(
            SOLAR_FLUX_W_M2 * 10.0 * 0.3 * 1.0 * 0.9
        )

    def test_battery_capped_at_capacity(self):
        model = PowerModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "battery_capacity_wh": 1000.0,
                "battery_charge_wh": 900.0,
            }
        )
        node = _node()
        delta = _tick(model, node, 0.0, 1.0)
        assert delta["battery_charge_wh"] == pytest.approx(1000.0)

    def test_eclipse_discharges_battery(self):
        model = PowerModel(
            {
                "enabled": True,
                "eclipse_fraction": 1.0,
                "battery_charge_wh": 500.0,
                "discharge_power_w": 100.0,
                "discharge_efficiency": 0.9,
            }
        )
        node = _node()
        delta = _tick(model, node, 100.0, 1.0)
        assert delta["power_available_w"] == pytest.approx(100.0)
        assert delta["battery_charge_wh"] == pytest.approx(500.0 - 100.0 / 0.9)

    def test_eclipse_no_generation(self):
        model = PowerModel(
            {"enabled": True, "eclipse_fraction": 1.0, "battery_charge_wh": 1000.0}
        )
        node = _node()
        delta = _tick(model, node, 100.0, 1.0)
        assert delta["power_available_w"] < SOLAR_FLUX_W_M2 * 10.0 * 0.3

    def test_battery_discharges_over_multiple_ticks(self):
        model = PowerModel(
            {
                "enabled": True,
                "eclipse_fraction": 1.0,
                "battery_charge_wh": 500.0,
                "discharge_power_w": 100.0,
            }
        )
        node = _node()
        charges = [_tick(model, node, float(i), 1.0)["battery_charge_wh"] for i in range(3)]
        assert charges[0] > charges[1] > charges[2] >= 0.0

    def test_charge_is_per_node(self):
        model = PowerModel(
            {"enabled": True, "eclipse_fraction": 0.0, "battery_capacity_wh": 1e9}
        )
        node_a = _node()
        node_b = RelayNode(NodeId("sat-2"))
        charge_a = _tick(model, node_a, 0.0, 1.0)["battery_charge_wh"]
        charge_b = _tick(model, node_b, 0.0, 1.0)["battery_charge_wh"]
        assert charge_a == charge_b

    def test_get_summary(self):
        summary = PowerModel({"enabled": True}).get_summary()
        assert summary["enabled"] is True
        assert "battery_capacity_wh" in summary

    def test_registered(self):
        assert "power" in STRATEGIES
        assert STRATEGIES["power"] is PowerModel
