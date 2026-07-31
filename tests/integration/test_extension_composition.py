from __future__ import annotations

from typing import Dict, List

import networkx as nx

from skynetra.foundation.types import NodeId
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES, get_router, list_routers


class CustomEchoRouter(RoutingEngine):
    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        if source in graph and destination in graph:
            return [source, destination]
        return []

    def name(self) -> str:
        return "echo"


class TestExtensionComposition:
    def test_custom_router_via_interface(self):
        router = CustomEchoRouter()
        assert isinstance(router, RoutingEngine)
        g = nx.Graph()
        g.add_node("A")
        g.add_node("B")
        assert router.compute_route(g, "A", "B") == ["A", "B"]

    def test_custom_router_no_path(self):
        router = CustomEchoRouter()
        g = nx.Graph()
        g.add_node("A")
        assert router.compute_route(g, "A", "B") == []

    def test_register_custom_router(self):
        STRATEGIES["echo"] = CustomEchoRouter
        try:
            assert "echo" in list_routers()
            loaded = get_router("echo")
            assert isinstance(loaded, CustomEchoRouter)
            assert loaded.name() == "echo"
        finally:
            STRATEGIES.pop("echo", None)

    def test_builtin_routers_available(self):
        routers = list_routers()
        assert "shortest_path" in routers
        assert "backpressure" in routers

    def test_get_builtin_router(self):
        sp = get_router("shortest_path")
        assert sp.name() == "shortest_path"

        bp = get_router("backpressure")
        assert bp.name() == "backpressure"

    def test_unknown_router_raises(self):
        import pytest
        with pytest.raises(KeyError, match="Unknown routing strategy"):
            get_router("nonexistent")

    def test_router_compute_route_contract(self):
        g = nx.Graph()
        g.add_node("A", position=(0.0, 0.0, 0.0))
        g.add_node("B", position=(1.0, 1.0, 1.0))
        g.add_edge("A", "B", quality=0.9)

        sp = get_router("shortest_path")
        path = sp.compute_route(g, "A", "B")
        assert isinstance(path, list)
        assert len(path) >= 2
        assert path[0] == "A"
        assert path[-1] == "B"

    def test_router_name_unique(self):
        names = set()
        for name in list_routers():
            router = get_router(name)
            n = router.name()
            assert n not in names, f"Duplicate name: {n}"
            names.add(n)
