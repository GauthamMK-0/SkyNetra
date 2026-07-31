from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.power import PowerModel
from skynetra.foundation.types import NodeId, Vector3


class TestPowerModel:
    def test_name(self):
        model = PowerModel()
        assert model.name() == "power"

    def test_apply_increases_power(self):
        model = PowerModel(solar_panel_area=10.0, efficiency=0.3)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(power_available=0.0),
        }
        result = model.apply(states, 1.0)
        solar_flux = 1361.0
        expected_generated = solar_flux * 10.0 * 0.3 * 1.0
        assert abs(result[NodeId("sat-1")].power_available - expected_generated) < 1e-9

    def test_apply_returns_all_states(self):
        model = PowerModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(),
            NodeId("sat-2"): PhysicsState(),
        }
        result = model.apply(states, 1.0)
        assert len(result) == 2

    def test_custom_panel_area(self):
        model = PowerModel(solar_panel_area=5.0, efficiency=0.2)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(power_available=0.0),
        }
        result = model.apply(states, 1.0)
        expected = 1361.0 * 5.0 * 0.2 * 1.0
        assert abs(result[NodeId("sat-1")].power_available - expected) < 1e-9

    def test_power_accumulates(self):
        model = PowerModel(solar_panel_area=1.0, efficiency=1.0)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(power_available=0.0),
        }
        for _ in range(3):
            states = model.apply(states, 1.0)
        assert abs(states[NodeId("sat-1")].power_available - 1361.0 * 3) < 1e-9

    def test_power_consumed_unchanged(self):
        model = PowerModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(power_consumed=300.0),
        }
        result = model.apply(states, 1.0)
        assert result[NodeId("sat-1")].power_consumed == 300.0

    def test_other_fields_preserved(self):
        model = PowerModel()
        pos: Vector3 = (7000.0, 0.0, 0.0)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(
                position=pos,
                temperature=300.0,
                radiation_dose=0.1,
            ),
        }
        result = model.apply(states, 1.0)
        s = result[NodeId("sat-1")]
        assert s.position == pos
        assert s.temperature == 300.0
        assert s.radiation_dose == 0.1

    def test_is_physics_model(self):
        from skynetra.engines.physics.interface import PhysicsModel
        assert isinstance(PowerModel(), PhysicsModel)

    def test_registered(self):
        from skynetra.engines.physics.registry import STRATEGIES
        assert "power" in STRATEGIES
        assert STRATEGIES["power"] is PowerModel
