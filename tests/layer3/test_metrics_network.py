from __future__ import annotations

from typing import Dict

import networkx as nx

from skynetra.domain.nodes.base import Node, PhysicsState
from skynetra.domain.nodes.relay import RelayNode
from skynetra.foundation.types import NodeId
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.network import NetworkMetricsCollector


class TestNetworkMetricsCollector:
    def test_name(self):
        collector = NetworkMetricsCollector()
        assert collector.name() == "network"

    def test_collect_empty_context(self):
        collector = NetworkMetricsCollector()
        ctx = SimulationContext()
        metrics = collector.collect(ctx)
        assert metrics["total_packets"] == 0
        assert metrics["total_dropped"] == 0
        assert metrics["edge_count"] == 0
        assert metrics["node_count"] == 0

    def test_collect_with_nodes(self):
        collector = NetworkMetricsCollector()
        node_a = RelayNode(NodeId("a"))
        node_b = RelayNode(NodeId("b"))
        node_a.metrics.packets_sent = 10
        node_b.metrics.packets_received = 5
        node_b.metrics.packets_dropped = 2

        ctx = SimulationContext(
            nodes={NodeId("a"): node_a, NodeId("b"): node_b},
            topology_graph=_make_graph(3),
        )
        metrics = collector.collect(ctx)
        assert metrics["total_packets"] == 15
        assert metrics["total_dropped"] == 2
        assert metrics["edge_count"] == 3
        assert metrics["node_count"] == 4

    def test_collect_topology_counts(self):
        collector = NetworkMetricsCollector()
        g = nx.Graph()
        g.add_node("x")
        g.add_node("y")
        g.add_edge("x", "y")
        ctx = SimulationContext(
            nodes={NodeId("x"): RelayNode(NodeId("x"))},
            topology_graph=g,
        )
        metrics = collector.collect(ctx)
        assert metrics["edge_count"] == 1
        assert metrics["node_count"] == 2

    def test_is_metrics_collector(self):
        from skynetra.orchestration.metrics.interface import MetricsCollector
        assert isinstance(NetworkMetricsCollector(), MetricsCollector)

    def test_registered(self):
        from skynetra.orchestration.metrics.registry import STRATEGIES
        assert "network" in STRATEGIES
        assert STRATEGIES["network"] is NetworkMetricsCollector


def _make_graph(num_edges: int) -> nx.Graph:
    g = nx.Graph()
    for i in range(num_edges + 1):
        g.add_node(f"n{i}")
    for i in range(num_edges):
        g.add_edge(f"n{i}", f"n{i+1}")
    return g
