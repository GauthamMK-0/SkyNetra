from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.nodes.ground import GroundStation
from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.results import SimulationResults
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.topology_metrics import TopologyMetricsCollector
from skynetra.foundation.types import NodeId


def test_shortest_path_simulation_returns_results():
    nodes: Dict[NodeId, Node] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
        NodeId("sat-3"): RelayNode(NodeId("sat-3")),
        NodeId("gs-1"): GroundStation(NodeId("gs-1")),
    }
    router = ShortestPathRouter()
    collectors = [NetworkMetricsCollector(), TopologyMetricsCollector()]

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        metrics_collectors=collectors,
        dt=1.0,
    )
    results = sim.run(duration=2.0)

    assert isinstance(results, SimulationResults)
    assert results.duration == 2.0
    assert "network" in results.metrics
    assert "topology" in results.metrics


def test_simulation_runs_with_single_node():
    nodes: Dict[NodeId, Node] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
    }
    router = ShortestPathRouter()
    sim = SkyNetraSimulation(nodes=nodes, routing_engine=router)
    results = sim.run(duration=0.5)
    assert results.duration == 0.5
    assert isinstance(results, SimulationResults)


def test_two_node_shortest_path():
    nodes: Dict[NodeId, Node] = {
        NodeId("a"): RelayNode(NodeId("a")),
        NodeId("b"): RelayNode(NodeId("b")),
    }
    router = ShortestPathRouter()
    sim = SkyNetraSimulation(nodes=nodes, routing_engine=router, dt=0.5)
    results = sim.run(duration=1.0)
    assert results.duration == 1.0
    assert isinstance(results, SimulationResults)
