from __future__ import annotations

import networkx as nx
import pytest

from skynetra.engines.routing.shortest_path import ShortestPathRouter
from skynetra.foundation.types import NodeId


@pytest.fixture
def router() -> ShortestPathRouter:
    return ShortestPathRouter()


@pytest.fixture
def simple_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_node("A", position=(0.0, 0.0, 7000.0))
    g.add_node("B", position=(1000.0, 0.0, 7000.0))
    g.add_node("C", position=(2000.0, 0.0, 7000.0))
    g.add_edge("A", "B", quality=0.9)
    g.add_edge("B", "C", quality=0.8)
    g.add_edge("A", "C", quality=0.1)
    return g


class TestShortestPathRouter:
    def test_name(self, router: ShortestPathRouter):
        assert router.name() == "shortest_path"

    def test_shortest_path_direct(self, router: ShortestPathRouter, simple_graph: nx.Graph):
        path = router.compute_route(simple_graph, "A", "B")
        assert path == ["A", "B"]

    def test_shortest_path_via_b(self, router: ShortestPathRouter, simple_graph: nx.Graph):
        path = router.compute_route(simple_graph, "A", "C")
        assert path == ["A", "C"] or path == ["A", "B", "C"]

    def test_no_path(self, router: ShortestPathRouter):
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        path = router.compute_route(g, "A", "B")
        assert path == []

    def test_same_source_destination(self, router: ShortestPathRouter, simple_graph: nx.Graph):
        path = router.compute_route(simple_graph, "A", "A")
        assert path == ["A"]

    def test_nonexistent_node(self, router: ShortestPathRouter, simple_graph: nx.Graph):
        path = router.compute_route(simple_graph, "A", "Z")
        assert path == []

    def test_is_routing_engine(self, router: ShortestPathRouter):
        from skynetra.engines.routing.interface import RoutingEngine
        assert isinstance(router, RoutingEngine)

    def test_registered(self):
        from skynetra.engines.routing.registry import STRATEGIES
        assert "shortest_path" in STRATEGIES
        assert STRATEGIES["shortest_path"] is ShortestPathRouter
