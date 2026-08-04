from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.doppler import DopplerModel
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.power import PowerModel
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.engines.physics.registry import STRATEGIES, build_physics_models
from skynetra.engines.physics.thermal import ThermalModel
from skynetra.foundation.errors import PhysicsModelError
from skynetra.foundation.types import LinkId, NodeId

CONSTELLATION = ConstellationConfig(
    n_planes=3, sats_per_plane=4, altitude_km=550.0, inclination_deg=53.0
)


def _node_registry() -> dict[NodeId, Node]:
    return {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
    }


def _graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node("sat-1", node_type="sat", position=(7000.0, 0.0, 0.0))
    graph.add_node("sat-2", node_type="sat", position=(0.0, 7000.0, 0.0))
    graph.add_edge("sat-1", "sat-2", capacity=10.0, propagation_delay_ms=1.0)
    graph.add_edge("sat-2", "sat-1", capacity=10.0, propagation_delay_ms=1.0)
    return graph


def _positions() -> dict[NodeId, tuple[float, float, float]]:
    return {
        NodeId("sat-1"): (7000.0, 0.0, 0.0),
        NodeId("sat-2"): (0.0, 7000.0, 0.0),
    }


class TestPhysicsOrchestrator:
    def test_filters_disabled_models(self):
        orchestrator = PhysicsOrchestrator(
            [ThermalModel(), DopplerModel({"enabled": True})]
        )
        assert len(orchestrator.models) == 1
        assert isinstance(orchestrator.models[0], DopplerModel)

    def test_run_tick_result_structure(self):
        orchestrator = PhysicsOrchestrator([ThermalModel({"enabled": True})])
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        assert set(result.keys()) == {
            "node_updates",
            "link_updates",
            "weight_overrides",
            "summary",
        }

    def test_no_models_enabled_returns_empty(self):
        orchestrator = PhysicsOrchestrator(
            [ThermalModel(), RadiationModel(), PowerModel(), DopplerModel()]
        )
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        assert result["node_updates"] == {}
        assert result["link_updates"] == {}
        assert result["weight_overrides"] == {}
        assert result["summary"] == {}

    def test_node_updates_merged_from_enabled_models(self):
        orchestrator = PhysicsOrchestrator(
            [
                ThermalModel(
                    {"enabled": True, "eclipse_fraction": 0.0, "solar_equilibrium_k": 320.0}
                ),
                RadiationModel({"enabled": True, "background_dose_rate_rad_s": 0.01}),
            ]
        )
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        for node_id in (NodeId("sat-1"), NodeId("sat-2")):
            assert "temperature_k" in result["node_updates"][node_id]
            assert "radiation_dose_rad" in result["node_updates"][node_id]

    def test_link_updates_from_enabled_models(self):
        orchestrator = PhysicsOrchestrator(
            [RadiationModel({"enabled": True, "background_dose_rate_rad_s": 0.01})]
        )
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        for link in ((NodeId("sat-1"), NodeId("sat-2")), (NodeId("sat-2"), NodeId("sat-1"))):
            assert "radiation_bit_error_rate" in result["link_updates"][link]

    def test_weight_overrides_only_from_enabled_doppler(self):
        orchestrator = PhysicsOrchestrator(
            [
                ThermalModel({"enabled": True}),
                DopplerModel({"enabled": True}),
            ]
        )
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        assert set(result["weight_overrides"].keys()) == {
            LinkId("sat-1->sat-2"),
            LinkId("sat-2->sat-1"),
        }

    def test_weight_overrides_empty_without_doppler(self):
        orchestrator = PhysicsOrchestrator([ThermalModel({"enabled": True})])
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        assert result["weight_overrides"] == {}

    def test_weight_overrides_nonzero_after_link_motion(self):
        orchestrator = PhysicsOrchestrator([DopplerModel({"enabled": True})])
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        assert result["weight_overrides"][LinkId("sat-1->sat-2")] == pytest.approx(0.0)
        moving = _positions()
        moving[NodeId("sat-2")] = (10.0, 7000.0, 0.0)
        result = orchestrator.run_tick(
            1.0, 1.0, _graph(), _node_registry(), moving, CONSTELLATION
        )
        assert result["weight_overrides"][LinkId("sat-1->sat-2")] > 0.0

    def test_summary_keyed_by_model_name(self):
        orchestrator = PhysicsOrchestrator(
            [ThermalModel({"enabled": True}), DopplerModel({"enabled": True})]
        )
        result = orchestrator.run_tick(
            0.0, 1.0, _graph(), _node_registry(), _positions(), CONSTELLATION
        )
        assert set(result["summary"].keys()) == {"ThermalModel", "DopplerModel"}
        assert result["summary"]["ThermalModel"]["enabled"] is True


class TestPhysicsRegistry:
    def test_strategy_names(self):
        assert set(STRATEGIES.keys()) == {"thermal", "radiation", "power", "doppler"}

    def test_build_known_models(self):
        models = build_physics_models(
            [
                {"name": "thermal"},
                {"name": "radiation", "config": {"background_dose_rate_rad_s": 0.5}},
                {"name": "power"},
                {"name": "doppler", "config": {"enabled": True}},
            ]
        )
        assert [type(m).__name__ for m in models] == [
            "ThermalModel",
            "RadiationModel",
            "PowerModel",
            "DopplerModel",
        ]
        assert models[0].enabled is False
        assert models[3].enabled is True

    def test_build_empty_specs(self):
        assert build_physics_models([]) == []

    def test_build_unknown_name_raises(self):
        with pytest.raises(PhysicsModelError) as excinfo:
            build_physics_models([{"name": "quantum_flux"}])
        assert "Unknown physics model 'quantum_flux'" in str(excinfo.value)
