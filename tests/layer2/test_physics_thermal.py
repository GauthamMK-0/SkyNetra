from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.thermal import ThermalModel
from skynetra.foundation.types import NodeId, Vector3


class TestThermalModel:
    def test_name(self):
        model = ThermalModel()
        assert model.name() == "thermal"

    def test_apply_returns_all_states(self):
        model = ThermalModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(temperature=300.0),
            NodeId("sat-2"): PhysicsState(temperature=280.0),
        }
        result = model.apply(states, 1.0)
        assert len(result) == 2
        assert NodeId("sat-1") in result
        assert NodeId("sat-2") in result

    def test_apply_moves_toward_equilibrium(self):
        model = ThermalModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(temperature=300.0),
        }
        result = model.apply(states, 1.0)
        temp = result[NodeId("sat-1")].temperature
        assert abs(temp - 300.0) < 1e-9

    def test_cold_node_warms_up(self):
        model = ThermalModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(temperature=200.0),
        }
        result = model.apply(states, 10.0)
        assert result[NodeId("sat-1")].temperature > 200.0

    def test_hot_node_cools_down(self):
        model = ThermalModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(temperature=400.0),
        }
        result = model.apply(states, 10.0)
        assert result[NodeId("sat-1")].temperature < 400.0

    def test_other_fields_preserved(self):
        model = ThermalModel()
        pos: Vector3 = (7000.0, 0.0, 0.0)
        vel: Vector3 = (0.0, 7.5, 0.0)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(
                position=pos,
                velocity=vel,
                temperature=300.0,
                radiation_dose=0.5,
                power_available=1000.0,
                power_consumed=500.0,
            ),
        }
        result = model.apply(states, 1.0)
        s = result[NodeId("sat-1")]
        assert s.position == pos
        assert s.velocity == vel
        assert s.radiation_dose == 0.5
        assert s.power_available == 1000.0
        assert s.power_consumed == 500.0

    def test_custom_albedo_emissivity(self):
        model = ThermalModel(albedo=0.5, emissivity=0.6)
        assert model._albedo == 0.5
        assert model._emissivity == 0.6

    def test_is_physics_model(self):
        from skynetra.engines.physics.interface import PhysicsModel
        assert isinstance(ThermalModel(), PhysicsModel)

    def test_registered(self):
        from skynetra.engines.physics.registry import STRATEGIES
        assert "thermal" in STRATEGIES
        assert STRATEGIES["thermal"] is ThermalModel
