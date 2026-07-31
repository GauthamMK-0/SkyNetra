from __future__ import annotations

from typing import Dict, List

from skynetra.domain.nodes.base import Node, PhysicsState
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.power import PowerModel
from skynetra.engines.physics.radiation import RadiationModel
from skynetra.engines.physics.thermal import ThermalModel
from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics.physics_metrics import PhysicsMetricsCollector


def _make_nodes() -> Dict[NodeId, Node]:
    sat1 = RelayNode(NodeId("sat-1"))
    sat1.physics = PhysicsState(
        position=(7000.0, 0.0, 0.0),
        velocity=(0.0, 7.5, 0.0),
        temperature=300.0,
        radiation_dose=0.0,
        power_available=100.0,
        power_consumed=50.0,
    )
    sat2 = RelayNode(NodeId("sat-2"))
    sat2.physics = PhysicsState(
        position=(0.0, 7000.0, 0.0),
        velocity=(-7.5, 0.0, 0.0),
        temperature=280.0,
        radiation_dose=0.1,
        power_available=200.0,
        power_consumed=80.0,
    )
    return {NodeId("sat-1"): sat1, NodeId("sat-2"): sat2}


def test_physics_simulation_updates_states():
    nodes = _make_nodes()
    router = ShortestPathRouter()
    models: List = [ThermalModel(), RadiationModel(background_dose_rate=0.01), PowerModel()]
    orchestrator = PhysicsOrchestrator(models)

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        physics_orchestrator=orchestrator,
        dt=1.0,
    )
    results = sim.run(duration=5.0)

    assert results.duration == 5.0
    updated_sat1 = nodes[NodeId("sat-1")]
    assert updated_sat1.physics is not None


def test_physics_metrics_collected():
    nodes = _make_nodes()
    router = ShortestPathRouter()
    orchestrator = PhysicsOrchestrator([ThermalModel()])

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        physics_orchestrator=orchestrator,
        metrics_collectors=[PhysicsMetricsCollector()],
    )
    results = sim.run(duration=2.0)

    assert "physics" in results.metrics
    assert results.metrics["physics"]["num_nodes"] == 2


def test_all_physics_models_applied():
    nodes = _make_nodes()
    router = ShortestPathRouter()
    models = [
        ThermalModel(albedo=0.3, emissivity=0.8),
        RadiationModel(background_dose_rate=0.005),
        PowerModel(solar_panel_area=5.0, efficiency=0.25),
    ]
    orchestrator = PhysicsOrchestrator(models)

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        physics_orchestrator=orchestrator,
        dt=0.5,
    )
    results = sim.run(duration=3.0)
    assert results.duration == 3.0
    sat1 = nodes[NodeId("sat-1")]

    # Temperature should change since initial != ThermalModel equilibrium (300K)
    initial_temp = 300.0
    assert sat1.physics.temperature == initial_temp, "temperature unchanged at equilibrium"

    # sat-2 starts at 280K, should warm toward equilibrium
    sat2 = nodes[NodeId("sat-2")]
    assert sat2.physics.temperature > 280.0
    assert sat1.physics.radiation_dose > 0.0
    assert sat1.physics.power_available > 100.0
