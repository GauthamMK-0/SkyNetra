from __future__ import annotations

from typing import Dict

import networkx as nx

from skynetra.domain.topology.graph import build_topology_graph
from skynetra.foundation.types import NodeId, Vector3


def _constant_quality(
    a: NodeId, b: NodeId, pa: Vector3, pb: Vector3
) -> float:
    return 0.8


def _variable_quality(
    a: NodeId, b: NodeId, pa: Vector3, pb: Vector3
) -> float:
    if a == NodeId("sat-1") and b == NodeId("sat-2"):
        return 0.9
    return 0.1


def test_build_empty_positions():
    graph = build_topology_graph(
        positions={}, quality_fn=_constant_quality
    )
    assert isinstance(graph, nx.Graph)
    assert graph.number_of_nodes() == 0


def test_build_single_node():
    positions = {NodeId("sat-1"): (7000.0, 0.0, 0.0)}
    graph = build_topology_graph(positions=positions, quality_fn=_constant_quality)
    assert graph.number_of_nodes() == 1
    assert graph.number_of_edges() == 0


def test_build_two_nodes_above_threshold():
    positions = {
        NodeId("sat-1"): (7000.0, 0.0, 0.0),
        NodeId("sat-2"): (0.0, 7000.0, 0.0),
    }
    graph = build_topology_graph(positions=positions, quality_fn=_constant_quality)
    assert graph.number_of_edges() == 1
    assert graph.has_edge(NodeId("sat-1"), NodeId("sat-2"))


def test_threshold_filters_edges():
    positions = {
        NodeId("sat-1"): (7000.0, 0.0, 0.0),
        NodeId("sat-2"): (0.0, 7000.0, 0.0),
    }

    def low_quality(
        a: NodeId, b: NodeId, pa: Vector3, pb: Vector3
    ) -> float:
        return 0.05

    graph = build_topology_graph(
        positions=positions, quality_fn=low_quality, threshold=0.5
    )
    assert graph.number_of_edges() == 0


def test_known_links_used():
    positions = {
        NodeId("a"): (0.0, 0.0, 0.0),
        NodeId("b"): (1.0, 0.0, 0.0),
        NodeId("c"): (2.0, 0.0, 0.0),
    }
    known = [(NodeId("a"), NodeId("c"))]
    graph = build_topology_graph(
        positions=positions,
        quality_fn=_constant_quality,
        known_links=known,
    )
    assert graph.has_edge(NodeId("a"), NodeId("b"))
    assert graph.has_edge(NodeId("a"), NodeId("c"))


def test_edge_quality_attributes():
    positions = {
        NodeId("a"): (0.0, 0.0, 0.0),
        NodeId("b"): (1.0, 0.0, 0.0),
    }

    def q_fn(a: NodeId, b: NodeId, pa: Vector3, pb: Vector3) -> float:
        return 0.75

    graph = build_topology_graph(positions=positions, quality_fn=q_fn)
    assert graph.edges[NodeId("a"), NodeId("b")]["quality"] == 0.75


def test_node_positions_stored():
    positions = {NodeId("sat-1"): (7000.0, 0.0, 0.0)}
    graph = build_topology_graph(positions=positions, quality_fn=_constant_quality)
    assert graph.nodes[NodeId("sat-1")]["position"] == (7000.0, 0.0, 0.0)
