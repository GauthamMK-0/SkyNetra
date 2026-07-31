from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.foundation.types import NodeId, Vector3


class TestRadiationModel:
    def test_name(self):
        model = RadiationModel()
        assert model.name() == "radiation"

    def test_apply_increases_dose(self):
        model = RadiationModel(background_dose_rate=0.01)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(radiation_dose=0.0),
        }
        result = model.apply(states, 10.0)
        assert result[NodeId("sat-1")].radiation_dose == 0.1

    def test_apply_returns_all_states(self):
        model = RadiationModel()
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(),
            NodeId("sat-2"): PhysicsState(),
        }
        result = model.apply(states, 1.0)
        assert len(result) == 2

    def test_custom_dose_rate(self):
        model = RadiationModel(background_dose_rate=0.5)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(radiation_dose=0.0),
        }
        result = model.apply(states, 2.0)
        assert result[NodeId("sat-1")].radiation_dose == 1.0

    def test_other_fields_preserved(self):
        model = RadiationModel()
        pos: Vector3 = (7000.0, 0.0, 0.0)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(
                position=pos,
                temperature=273.15,
                power_available=500.0,
                power_consumed=200.0,
            ),
        }
        result = model.apply(states, 1.0)
        s = result[NodeId("sat-1")]
        assert s.position == pos
        assert s.temperature == 273.15
        assert s.power_available == 500.0
        assert s.power_consumed == 200.0

    def test_dose_accumulates_over_multiple_calls(self):
        model = RadiationModel(background_dose_rate=0.01)
        states: Dict[NodeId, PhysicsState] = {
            NodeId("sat-1"): PhysicsState(radiation_dose=0.0),
        }
        for _ in range(5):
            states = model.apply(states, 1.0)
        assert abs(states[NodeId("sat-1")].radiation_dose - 0.05) < 1e-12

    def test_is_physics_model(self):
        from skynetra.engines.physics.interface import PhysicsModel
        assert isinstance(RadiationModel(), PhysicsModel)

    def test_registered(self):
        from skynetra.engines.physics.registry import STRATEGIES
        assert "radiation" in STRATEGIES
        assert STRATEGIES["radiation"] is RadiationModel
