from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStation
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.routing.backpressure import BackPressureRouter
from skynetra.engines.workload.ai_training import AITrainingWorkload
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.results import SimulationResults


def test_backpressure_simulation_returns_results():
    nodes: Dict[NodeId, Node] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
        NodeId("gs-1"): GroundStation(NodeId("gs-1")),
    }
    router = BackPressureRouter()
    router.update_backlog("sat-1->sat-2", 5.0)
    router.update_backlog("sat-2->gs-1", 3.0)

    profile = WorkloadProfile(name="test", packet_size_bytes=256)
    workload = AITrainingWorkload(profile)

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        workload_generators=[workload],
        metrics_collectors=[NetworkMetricsCollector()],
        dt=1.0,
    )
    results = sim.run(duration=3.0)

    assert isinstance(results, SimulationResults)
    assert results.duration == 3.0


def test_backpressure_multiple_updates():
    nodes: Dict[NodeId, Node] = {
        NodeId("a"): RelayNode(NodeId("a")),
        NodeId("b"): RelayNode(NodeId("b")),
        NodeId("c"): RelayNode(NodeId("c")),
    }
    router = BackPressureRouter()
    router.update_backlog("a->b", 10.0)
    router.update_backlog("b->c", 20.0)
    router.update_backlog("a->c", 5.0)

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        dt=0.5,
    )
    results = sim.run(duration=1.0)
    assert results.duration == 1.0


def test_backpressure_with_workload_produces_metrics():
    nodes: Dict[NodeId, Node] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
    }
    router = BackPressureRouter()
    profile = WorkloadProfile(name="bp-test", packet_size_bytes=128, ttl=10)
    workload = AITrainingWorkload(profile)

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        workload_generators=[workload],
        metrics_collectors=[NetworkMetricsCollector()],
    )
    results = sim.run(duration=2.0)
    assert "network" in results.metrics
