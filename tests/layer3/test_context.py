from __future__ import annotations

import networkx as nx
import simpy

from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import LinkId, NodeId
from skynetra.orchestration.context import SimulationContext


class TestSimulationContext:
    def test_default_construction(self):
        ctx = SimulationContext(env=simpy.Environment())
        assert ctx.env is not None
        assert isinstance(ctx.event_bus, EventBus)
        assert ctx.node_registry == {}
        assert isinstance(ctx.graph, nx.Graph)
        assert ctx.graph.number_of_nodes() == 0
        assert ctx.routing_engine is None
        assert ctx.physics_orchestrator is None
        assert ctx.metrics_aggregator is None
        assert ctx.sim_duration_s == 60.0
        assert ctx.topology_update_interval_s == 10.0
        assert ctx.physics_tick_interval_s == 1.0
        assert ctx.seed == 42
        assert ctx.constellation is None
        assert ctx.propagator is None
        assert ctx.pod_ids == []
        assert ctx.ground_station_ids == []
        assert ctx.current_time_s == 0.0
        assert ctx.topology_version == 0
        assert ctx.combined_weight_overrides == {}
        assert ctx.debug_routing is False
        assert ctx.scratchpad == {}

    def test_custom_values(self):
        from skynetra.domain.nodes.relay import RelayNode
        from skynetra.engines.routing.shortest_path import ShortestPathRouter

        bus = EventBus()
        ctx = SimulationContext(
            env=simpy.Environment(),
            event_bus=bus,
            node_registry={NodeId("a"): RelayNode(NodeId("a"))},
            routing_engine=ShortestPathRouter(),
            sim_duration_s=120.0,
            topology_update_interval_s=5.0,
            physics_tick_interval_s=0.5,
            seed=7,
            pod_ids=[NodeId("pod-1")],
            ground_station_ids=[NodeId("gs-1")],
            debug_routing=True,
        )
        assert ctx.event_bus is bus
        assert ctx.sim_duration_s == 120.0
        assert ctx.topology_update_interval_s == 5.0
        assert ctx.physics_tick_interval_s == 0.5
        assert ctx.seed == 7
        assert ctx.pod_ids == [NodeId("pod-1")]
        assert ctx.debug_routing is True

    def test_scratchpad_is_independent_per_context(self):
        first = SimulationContext(env=simpy.Environment())
        second = SimulationContext(env=simpy.Environment())
        first.scratchpad["marker"] = 1
        assert "marker" not in second.scratchpad

    def test_scratchpad_mutable(self):
        ctx = SimulationContext(env=simpy.Environment())
        ctx.scratchpad["note"] = {"a": 1}
        ctx.scratchpad["note"]["b"] = 2
        assert ctx.scratchpad["note"] == {"a": 1, "b": 2}

    def test_combined_weight_overrides_mutable(self):
        ctx = SimulationContext(env=simpy.Environment())
        ctx.combined_weight_overrides[LinkId("a->b")] = 5.0
        assert ctx.combined_weight_overrides == {LinkId("a->b"): 5.0}

    def test_mutability_of_runtime_fields(self):
        ctx = SimulationContext(env=simpy.Environment())
        ctx.current_time_s = 42.0
        ctx.topology_version = 3
        assert ctx.current_time_s == 42.0
        assert ctx.topology_version == 3
