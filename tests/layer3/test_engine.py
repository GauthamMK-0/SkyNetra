from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import ReferenceCircularPropagator
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.registry import build_physics_models
from skynetra.engines.routing.registry import get_routing_engine
from skynetra.engines.workload.ai_training import AITrainingSyncWorkload
from skynetra.engines.workload.inference import InferenceQueryWorkload
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import (
    PhysicsTickEvent,
    TopologyUpdateEvent,
)
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.physics_metrics import PhysicsMetricsCollector
from skynetra.orchestration.results import SimulationResults

CONSTELLATION_3X6 = ConstellationConfig(
    n_planes=3, sats_per_plane=6, altitude_km=550, inclination_deg=55
)

AI_TRAINING_SYNC_ONE_ROUND = AITrainingSyncWorkload(
    {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 1.0}
)


def _build_registry(n_pods: int = 2, n_gs: int = 1) -> Dict[NodeId, Node]:
    propagator = ReferenceCircularPropagator()
    registry: Dict[NodeId, Node] = {
        sat_id: RelayNode(sat_id) for sat_id in propagator.get_sat_ids(CONSTELLATION_3X6)
    }
    for index in range(1, n_pods + 1):
        registry[NodeId(f"pod-{index}")] = PodNode(NodeId(f"pod-{index}"))
    for index in range(1, n_gs + 1):
        registry[NodeId(f"gs-{index}")] = GroundStationNode(NodeId(f"gs-{index}"))
    return registry


def _shortest_path_sim(**kwargs: object) -> OrbitDCSimulation:
    return OrbitDCSimulation.from_layers(
        constellation=CONSTELLATION_3X6,
        node_registry=_build_registry(),
        routing_engine=get_routing_engine("shortest_path"),
        **kwargs,
    )


class TestRun:
    def test_shortest_path_no_physics_delivers_packets(self):
        sim = _shortest_path_sim(
            workloads=[AI_TRAINING_SYNC_ONE_ROUND],
            sim_duration_s=60.0,
        )
        results = sim.run()

        assert isinstance(results, SimulationResults)
        assert results.duration == 60.0
        network = results.engine_metrics["network_metrics"]
        assert network["delivered"] > 0
        assert network["dropped"] == 0
        assert any(ev.event_type == "packet_delivered" for ev in results.events)

    def test_default_network_collector_when_none_provided(self):
        sim = _shortest_path_sim(
            workloads=[AI_TRAINING_SYNC_ONE_ROUND],
            sim_duration_s=10.0,
            metrics_collectors=None,
        )
        results = sim.run()
        assert "network_metrics" in results.engine_metrics

    def test_backpressure_router_runs_without_crash(self):
        sim = OrbitDCSimulation.from_layers(
            constellation=CONSTELLATION_3X6,
            node_registry=_build_registry(),
            routing_engine=get_routing_engine("backpressure"),
            workloads=[AI_TRAINING_SYNC_ONE_ROUND],
            sim_duration_s=30.0,
        )
        results = sim.run()

        assert isinstance(results, SimulationResults)
        assert results.duration == 30.0
        assert "network_metrics" in results.engine_metrics
        assert not [ev for ev in results.events if ev.event_type == "engine_error"]

    def test_thermal_and_radiation_physics_run(self):
        physics = PhysicsOrchestrator(
            build_physics_models(
                [
                    {"name": "thermal", "config": {"enabled": True}},
                    {"name": "radiation", "config": {"enabled": True}},
                ]
            )
        )
        sim = OrbitDCSimulation.from_layers(
            constellation=CONSTELLATION_3X6,
            node_registry=_build_registry(),
            routing_engine=get_routing_engine("shortest_path"),
            physics_orchestrator=physics,
            workloads=[
                InferenceQueryWorkload(
                    {
                        "arrival_pattern": "bursty",
                        "burst_size": 2,
                        "burst_interval_s": 5.0,
                        "burst_idle_s": 20.0,
                        "seed": 7,
                    }
                )
            ],
            metrics_collectors=[
                NetworkMetricsCollector(),
                PhysicsMetricsCollector(),
            ],
            sim_duration_s=60.0,
        )
        results = sim.run()

        physics_metrics = results.engine_metrics["physics_metrics"]
        assert set(physics_metrics["active_models"]) == {
            "ThermalModel",
            "RadiationModel",
        }
        assert isinstance(physics_metrics["thermal_throttle_events"], int)
        assert isinstance(physics_metrics["radiation_fault_events"], int)
        assert isinstance(physics_metrics["avg_temperature"], float)
        assert any(ev.event_type == "physics_tick" for ev in results.events)

    def test_from_spec_full_pipeline(self):
        spec = OrbitDCSimulation.SimulationSpec(
            constellation=CONSTELLATION_3X6,
            n_pods=2,
            n_ground_stations=2,
            physics_specs=[{"name": "thermal", "config": {"enabled": True}}],
            workload_specs=[
                {
                    "name": "ai_training_sync",
                    "config": {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 1.0},
                }
            ],
            metrics_specs=[
                {"name": "network_metrics"},
                {"name": "physics_metrics"},
                {"name": "compute_metrics"},
                {"name": "topology_metrics"},
            ],
            sim_duration_s=30.0,
        )
        sim = OrbitDCSimulation.from_spec(spec)
        results = sim.run()

        assert isinstance(results, SimulationResults)
        assert "network_metrics" in results.engine_metrics
        assert "physics_metrics" in results.engine_metrics
        assert "compute_metrics" in results.engine_metrics
        assert "topology_metrics" in results.engine_metrics
        assert results.engine_metrics["network_metrics"]["delivered"] > 0

    def test_results_to_dict_and_compare(self):
        first = _shortest_path_sim(
            workloads=[AI_TRAINING_SYNC_ONE_ROUND], sim_duration_s=30.0
        ).run()
        second = _shortest_path_sim(
            workloads=[AI_TRAINING_SYNC_ONE_ROUND], sim_duration_s=60.0
        ).run()

        dumped = first.to_dict()
        assert dumped["duration"] == 30.0
        assert "engine_metrics" in dumped
        assert "events" in dumped
        assert all({"time", "event_type"} <= set(ev) for ev in dumped["events"])

        diffs = first.compare(second)
        assert "duration" in diffs
        assert first.compare(first) == {}


class TestSetup:
    def test_setup_builds_context(self):
        sim = _shortest_path_sim(sim_duration_s=5.0)
        context = sim.setup()

        assert context.topology_version == 0
        assert context.graph.number_of_nodes() > 0
        assert len(context.pod_ids) == 2
        assert context.scratchpad["sim_duration_s"] == 5.0
        assert context.scratchpad["metrics_snapshots"] == []

    def test_setup_is_idempotent(self):
        sim = _shortest_path_sim(sim_duration_s=5.0)
        assert sim.setup() is sim.setup()

    def test_run_publishes_topology_events_and_scratchpad(self):
        sim = _shortest_path_sim(workloads=[AI_TRAINING_SYNC_ONE_ROUND], sim_duration_s=25.0)
        results = sim.run()
        topology_events = [ev for ev in results.events if isinstance(ev, TopologyUpdateEvent)]
        assert len(topology_events) == 2  # t=10, t=20 (t=25 not fired)
        context = sim.setup()
        assert context.scratchpad["topology_version"] == 2
        assert len(context.scratchpad["metrics_snapshots"]) > 0

    def test_physics_tick_events_carry_node_state(self):
        physics = PhysicsOrchestrator(
            build_physics_models([{"name": "thermal", "config": {"enabled": True}}])
        )
        sim = OrbitDCSimulation.from_layers(
            constellation=CONSTELLATION_3X6,
            node_registry=_build_registry(),
            routing_engine=get_routing_engine("shortest_path"),
            physics_orchestrator=physics,
            sim_duration_s=5.0,
        )
        results = sim.run()
        physics_events = [ev for ev in results.events if isinstance(ev, PhysicsTickEvent)]
        assert len(physics_events) == 4  # t=1..4
        sample = next(iter(physics_events[0].node_state.values()))
        assert "temperature_k" in sample["physics_state"]
        assert "energy_consumed" in sample["metrics_state"]
        assert physics_events[0].active_models == ["ThermalModel"]
