"""Integration: extension composition via from_layers().

Third-party strategies (EnergyAwareRouter, DebrisProximityModel,
FLMetricsCollector from extensions_examples/) are composed WITHOUT any
registry mutation, by passing instances directly to
OrbitDCSimulation.from_layers() — the preferred extension path for a
layered architecture.

Also verifies Python ABC enforcement: a subclass missing a required
abstract method raises TypeError at instantiation (the layered
architecture has no METADATA/registry validation step, so ABC
enforcement is the guard against incomplete extensions).
"""

from __future__ import annotations

import pytest

from extensions_examples.debris_proximity_model import DebrisProximityModel
from extensions_examples.energy_aware_router import EnergyAwareRouter
from extensions_examples.fl_metrics_collector import FLMetricsCollector
from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import ReferenceCircularPropagator
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.metrics.interface import MetricsCollector


def _make_node_registry() -> dict[NodeId, Node]:
    constellation = ConstellationConfig(
        n_planes=2, sats_per_plane=3, altitude_km=550.0, inclination_deg=55.0
    )
    registry: dict[NodeId, Node] = {
        sat_id: RelayNode(sat_id)
        for sat_id in ReferenceCircularPropagator().get_sat_ids(constellation)
    }
    registry[NodeId("pod-1")] = PodNode(NodeId("pod-1"))
    registry[NodeId("pod-2")] = PodNode(NodeId("pod-2"))
    registry[NodeId("gs-1")] = GroundStationNode(NodeId("gs-1"))
    return registry


def _build_sim(
    metrics: list[MetricsCollector] | None = None,
    routing: RoutingEngine | None = None,
    physics: PhysicsOrchestrator | None = None,
) -> OrbitDCSimulation:
    constellation = ConstellationConfig(
        n_planes=2, sats_per_plane=3, altitude_km=550.0, inclination_deg=55.0
    )
    return OrbitDCSimulation.from_layers(
        constellation=constellation,
        node_registry=_make_node_registry(),
        routing_engine=routing or EnergyAwareRouter({"power_threshold_w": 150.0}),
        physics_orchestrator=physics,
        workloads=[
            FederatedLearningWorkload(
                {"round_interval_s": 10.0, "n_rounds": 3, "aggregate_time_s": 1.0}
            )
        ],
        metrics_collectors=metrics or [],
        sim_duration_s=60.0,
        topology_update_interval_s=10.0,
        physics_tick_interval_s=1.0,
        seed=7,
    )


def test_from_layers_with_custom_engines() -> None:
    fl_collector = FLMetricsCollector()
    results = _build_sim(
        metrics=[fl_collector],
        physics=PhysicsOrchestrator(
            [DebrisProximityModel({"enabled": True, "seed": 7, "collision_probability": 0.02})]
        ),
    ).run()

    assert results.duration == 60.0
    assert "fl_metrics" in results.engine_metrics
    fl = results.engine_metrics["fl_metrics"]
    assert fl["rounds_completed"] >= 0
    assert fl["mean_round_time_s"] >= 0
    assert fl["aggregation_latency_ms"] >= 0
    assert fl["stragglers_per_round"] >= 0


def test_fl_collector_tracks_gradient_rounds() -> None:
    fl_collector = FLMetricsCollector()
    results = _build_sim(metrics=[fl_collector]).run()
    fl = results.engine_metrics["fl_metrics"]
    # 3 FL rounds with round_interval_s=10 in a 60s run; fl_gather
    # gradients are delivered pod-to-pod, so rounds must have completed.
    assert fl["rounds_completed"] > 0


def test_abstract_subclass_without_all_methods_raises() -> None:
    class IncompleteRouter(RoutingEngine):
        pass

    class IncompletePhysicsModel(PhysicsModel):
        pass

    class IncompleteCollector(MetricsCollector):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteRouter()
    with pytest.raises(TypeError):
        IncompletePhysicsModel()
    with pytest.raises(TypeError):
        IncompleteCollector()


def test_custom_strategies_are_instances_of_public_interfaces() -> None:
    router = EnergyAwareRouter({"power_threshold_w": 150.0})
    assert isinstance(router, RoutingEngine)
    assert router.power_threshold_w == 150.0

    model = DebrisProximityModel({"enabled": True})
    assert isinstance(model, PhysicsModel)
    assert model.enabled is True

    collector = FLMetricsCollector()
    assert isinstance(collector, MetricsCollector)
    assert collector.name == "fl_metrics"
