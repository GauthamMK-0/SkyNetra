from __future__ import annotations

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.engines.physics.thermal import ThermalModel
from skynetra.foundation.types import NodeId

CONSTELLATION = ConstellationConfig(
    n_planes=3, sats_per_plane=4, altitude_km=550.0, inclination_deg=53.0
)


def _node() -> RelayNode:
    return RelayNode(NodeId("sat-1"))


def _tick(
    model: ThermalModel,
    node: Node,
    time_s: float,
    dt_s: float,
    constellation: ConstellationConfig = CONSTELLATION,
) -> dict[str, float]:
    return model.compute_node_physics(
        node.node_id, node, None, time_s, dt_s, constellation
    )


class TestThermalModel:
    def test_is_physics_model(self):
        assert isinstance(ThermalModel(), PhysicsModel)

    def test_defaults_to_disabled(self):
        assert ThermalModel().enabled is False
        assert ThermalModel({"enabled": False}).enabled is False

    def test_enabled_flag_from_config(self):
        assert ThermalModel({"enabled": True}).enabled is True

    def test_disabled_returns_unchanged_state(self):
        node = _node()
        result = _tick(ThermalModel(), node, 100.0, 60.0)
        assert result == dict(node.physics_state)

    def test_sunlight_raises_temperature(self):
        model = ThermalModel(
            {"enabled": True, "eclipse_fraction": 0.0, "solar_equilibrium_k": 320.0}
        )
        node = _node()
        temp = _tick(model, node, 100.0, 3600.0)["temperature_k"]
        assert temp > node.physics_state["temperature_k"]

    def test_eclipse_cools_temperature(self):
        model = ThermalModel(
            {"enabled": True, "eclipse_fraction": 1.0, "eclipse_equilibrium_k": 200.0}
        )
        node = _node()
        node.update_physics({"temperature_k": 300.0})
        temp = _tick(model, node, 100.0, 3600.0)["temperature_k"]
        assert temp < 300.0

    def test_sunlight_and_eclipse_cycle(self):
        model = ThermalModel(
            {"enabled": True, "eclipse_fraction": 0.5, "eclipse_equilibrium_k": 200.0}
        )
        node = _node()
        period = 2.0 * 3.141592653589793 * ((6371.0 + 550.0) ** 3 / 3.986004418e5) ** 0.5
        in_sun = _tick(model, node, 0.75 * period, 3600.0)["temperature_k"]
        in_eclipse = _tick(model, node, 0.25 * period, 3600.0)["temperature_k"]
        assert in_sun > node.physics_state["temperature_k"]
        assert in_eclipse < in_sun

    def test_full_albedo_blocks_solar_heating(self):
        model = ThermalModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "albedo": 1.0,
                "solar_equilibrium_k": 320.0,
            }
        )
        node = _node()
        temp = _tick(model, node, 100.0, 3600.0)["temperature_k"]
        assert temp == pytest.approx(node.physics_state["temperature_k"])

    def test_zero_emissivity_blocks_eclipse_cooling(self):
        model = ThermalModel(
            {
                "enabled": True,
                "eclipse_fraction": 1.0,
                "emissivity": 0.0,
                "eclipse_equilibrium_k": 200.0,
            }
        )
        node = _node()
        node.update_physics({"temperature_k": 300.0})
        temp = _tick(model, node, 100.0, 3600.0)["temperature_k"]
        assert temp == pytest.approx(300.0)

    def test_get_summary(self):
        model = ThermalModel({"enabled": True})
        summary = model.get_summary()
        assert summary["enabled"] is True
        assert "albedo" in summary
        assert "eclipse_fraction" in summary

    def test_registered(self):
        assert "thermal" in STRATEGIES
        assert STRATEGIES["thermal"] is ThermalModel


class TestThermalThrottle:
    def test_high_temperature_degrades_pod_flops(self):
        """Thermal output feeds PodNode FLOPS degradation: the effective
        compute must match Layer 1's own formula exactly.
        """
        pod = PodNode(NodeId("pod-1"), flops=1e12)
        model = ThermalModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "solar_equilibrium_k": 350.0,
                "time_constant_s": 3600.0,
                "albedo": 0.0,
            }
        )
        delta = _tick(model, pod, 0.0, 3600.0)
        pod.update_physics(delta)
        assert pod.physics_state["temperature_k"] == pytest.approx(350.0)

        effective = pod.available_compute_flops()
        expected = pod.flops * pod.thermal_degradation_factor()
        assert effective == pytest.approx(expected)
        assert effective < pod.flops

    def test_nominal_temperature_keeps_full_flops(self):
        pod = PodNode(NodeId("pod-1"), flops=1e12)
        model = ThermalModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "solar_equilibrium_k": 293.15,
            }
        )
        pod.update_physics(_tick(model, pod, 0.0, 3600.0))
        assert pod.available_compute_flops() == pytest.approx(pod.flops)

    def test_extreme_temperature_drives_fault(self):
        pod = PodNode(NodeId("pod-1"))
        model = ThermalModel(
            {
                "enabled": True,
                "eclipse_fraction": 0.0,
                "solar_equilibrium_k": 500.0,
                "time_constant_s": 1.0,
            }
        )
        pod.update_physics(_tick(model, pod, 0.0, 1.0))
        assert pod.physics_state["temperature_k"] >= 400.0
        assert pod.is_operational() is False
