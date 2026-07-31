from __future__ import annotations

from typing import Dict

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.results import SimulationResults


@pytest.fixture
def two_node_simulation() -> SkyNetraSimulation:
    nodes: Dict[NodeId, Node] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
    }
    router = ShortestPathRouter()
    return SkyNetraSimulation(nodes=nodes, routing_engine=router)


class TestSkyNetraSimulation:
    def test_run_returns_simulation_results(self, two_node_simulation: SkyNetraSimulation):
        results = two_node_simulation.run(duration=1.0)
        assert isinstance(results, SimulationResults)

    def test_run_sets_duration(self, two_node_simulation: SkyNetraSimulation):
        results = two_node_simulation.run(duration=5.0)
        assert results.duration == 5.0

    def test_run_returns_metrics(self, two_node_simulation: SkyNetraSimulation):
        results = two_node_simulation.run(duration=1.0)
        assert isinstance(results.metrics, dict)

    def test_run_with_metrics_collectors(self):
        from skynetra.orchestration.metrics.network import NetworkMetricsCollector
        nodes: Dict[NodeId, Node] = {
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        router = ShortestPathRouter()
        sim = SkyNetraSimulation(
            nodes=nodes,
            routing_engine=router,
            metrics_collectors=[NetworkMetricsCollector()],
        )
        results = sim.run(duration=1.0)
        assert "network" in results.metrics

    def test_from_layers_alternative_constructor(self):
        nodes: Dict[NodeId, Node] = {
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        router = ShortestPathRouter()
        sim = SkyNetraSimulation.from_layers(nodes=nodes, routing_engine=router, dt=0.5)
        results = sim.run(duration=1.0)
        assert results.duration == 1.0

    def test_run_zero_duration(self, two_node_simulation: SkyNetraSimulation):
        results = two_node_simulation.run(duration=0.001)
        assert results.duration == 0.001

    def test_context_initialized(self, two_node_simulation: SkyNetraSimulation):
        ctx = two_node_simulation._context
        assert ctx.current_time == 0.0
        assert len(ctx.nodes) == 2
