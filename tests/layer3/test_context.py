from __future__ import annotations

import networkx as nx

from skynetra.orchestration.context import SimulationContext
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId


class TestSimulationContext:
    def test_default_construction(self):
        ctx = SimulationContext()
        assert ctx.nodes == {}
        assert isinstance(ctx.topology_graph, nx.Graph)
        assert ctx.topology_graph.number_of_nodes() == 0
        assert ctx.routing_engine is None
        assert ctx.physics_orchestrator is None
        assert ctx.workload_generators == []
        assert isinstance(ctx.event_bus, EventBus)
        assert ctx.current_time == 0.0
        assert ctx.dt == 1.0
        assert ctx.metadata == {}

    def test_custom_values(self):
        from skynetra.domain.nodes.relay import RelayNode
        from skynetra.engines.routing.shortest_path import ShortestPathRouter

        nodes = {NodeId("a"): RelayNode(NodeId("a"))}
        graph = nx.Graph()
        graph.add_node("a")
        router = ShortestPathRouter()
        bus = EventBus()

        ctx = SimulationContext(
            nodes=nodes,
            topology_graph=graph,
            routing_engine=router,
            event_bus=bus,
            current_time=10.0,
            dt=2.0,
            metadata={"key": "value"},
        )
        assert ctx.nodes == nodes
        assert ctx.topology_graph is graph
        assert ctx.routing_engine is router
        assert ctx.event_bus is bus
        assert ctx.current_time == 10.0
        assert ctx.dt == 2.0
        assert ctx.metadata == {"key": "value"}

    def test_nodes_mutable(self):
        ctx = SimulationContext()
        node_id = NodeId("sat-1")
        from skynetra.domain.nodes.relay import RelayNode
        ctx.nodes[node_id] = RelayNode(node_id)
        assert node_id in ctx.nodes

    def test_current_time_mutable(self):
        ctx = SimulationContext()
        ctx.current_time = 100.0
        assert ctx.current_time == 100.0

    def test_dt_mutable(self):
        ctx = SimulationContext()
        ctx.dt = 0.1
        assert ctx.dt == 0.1
