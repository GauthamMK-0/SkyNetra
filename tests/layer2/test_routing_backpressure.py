from __future__ import annotations

import networkx as nx

from skynetra.engines.routing.backpressure import BackPressureRouter


class TestBackPressureRouter:
    def test_name(self):
        router = BackPressureRouter()
        assert router.name() == "backpressure"

    def test_initial_backlog_empty(self):
        router = BackPressureRouter()
        assert router._queue_backlog == {}

    def test_update_backlog(self):
        router = BackPressureRouter()
        router.update_backlog("A->B", 10.0)
        assert router._queue_backlog["A->B"] == 10.0

    def test_update_backlog_accumulates(self):
        router = BackPressureRouter()
        router.update_backlog("A->B", 5.0)
        router.update_backlog("A->B", 3.0)
        assert router._queue_backlog["A->B"] == 8.0

    def test_route_simple(self):
        router = BackPressureRouter()
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_edge("A", "B")
        path = router.compute_route(g, "A", "B")
        assert path == ["A", "B"]

    def test_route_with_backlog_preference(self):
        router = BackPressureRouter()
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("B", "C")
        router.update_backlog("A->B", 100.0)
        router.update_backlog("A->C", 1.0)
        path = router.compute_route(g, "A", "C")
        assert path == ["A", "C"]

    def test_no_path(self):
        router = BackPressureRouter()
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        path = router.compute_route(g, "A", "B")
        assert path == []

    def test_same_source_destination(self):
        router = BackPressureRouter()
        g = nx.Graph()
        g.add_node("A")
        path = router.compute_route(g, "A", "A")
        assert path == ["A"]

    def test_route_multiple_hops(self):
        router = BackPressureRouter()
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_node("D")
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "D")
        router.update_backlog("A->B", 10.0)
        router.update_backlog("B->C", 20.0)
        path = router.compute_route(g, "A", "D")
        assert path == ["A", "B", "C", "D"]

    def test_stuck_at_dead_end(self):
        router = BackPressureRouter()
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")
        g.add_edge("A", "B")
        path = router.compute_route(g, "A", "C")
        assert path == []

    def test_is_routing_engine(self):
        from skynetra.engines.routing.interface import RoutingEngine
        assert isinstance(BackPressureRouter(), RoutingEngine)

    def test_registered(self):
        from skynetra.engines.routing.registry import STRATEGIES
        assert "backpressure" in STRATEGIES
        assert STRATEGIES["backpressure"] is BackPressureRouter
