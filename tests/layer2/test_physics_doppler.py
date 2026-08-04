from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.topology.isl import SPEED_OF_LIGHT_KM_S
from skynetra.engines.physics.doppler import DopplerModel
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import LinkId, NodeId

CARRIER_FREQ_HZ = 30e9


def _node_registry() -> dict[NodeId, Node]:
    return {
        NodeId("a"): RelayNode(NodeId("a")),
        NodeId("b"): RelayNode(NodeId("b")),
    }


def _graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node("a", node_type="sat", position=(7000.0, 0.0, 0.0))
    graph.add_node("b", node_type="sat", position=(0.0, 7000.0, 0.0))
    graph.add_edge("a", "b", capacity=10.0, propagation_delay_ms=1.0)
    graph.add_edge("b", "a", capacity=10.0, propagation_delay_ms=1.0)
    return graph


class TestDopplerModel:
    def test_is_physics_model(self):
        assert isinstance(DopplerModel(), PhysicsModel)

    def test_defaults_to_disabled(self):
        assert DopplerModel().enabled is False

    def test_disabled_link_physics_empty(self):
        assert DopplerModel().compute_link_physics(
            NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0
        ) == {}

    def test_disabled_returns_unchanged_node_state(self):
        node = RelayNode(NodeId("a"))
        assert DopplerModel().compute_node_physics(
            node.node_id, node, None, 0.0, 1.0, None
        ) == dict(node.physics_state)

    def test_first_tick_zero_shift(self):
        model = DopplerModel({"enabled": True})
        delta = model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        assert delta["doppler_shift_hz"] == 0.0

    def test_closing_link_positive_shift(self):
        model = DopplerModel({"enabled": True})
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        delta = model.compute_link_physics(NodeId("a"), NodeId("b"), 1010.0, 1.0, 1.0)
        expected = CARRIER_FREQ_HZ * (10.0 / 1.0) / SPEED_OF_LIGHT_KM_S
        assert delta["doppler_shift_hz"] == pytest.approx(expected)
        assert delta["doppler_shift_hz"] > 0.0

    def test_receding_link_negative_shift(self):
        model = DopplerModel({"enabled": True})
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        delta = model.compute_link_physics(NodeId("a"), NodeId("b"), 990.0, 1.0, 1.0)
        assert delta["doppler_shift_hz"] < 0.0

    def test_stationary_link_zero_shift(self):
        model = DopplerModel({"enabled": True})
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        delta = model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 1.0, 1.0)
        assert delta["doppler_shift_hz"] == 0.0

    def test_custom_carrier_freq(self):
        model = DopplerModel({"enabled": True, "carrier_freq_hz": 10e9})
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        delta = model.compute_link_physics(NodeId("a"), NodeId("b"), 1010.0, 1.0, 1.0)
        expected = 10e9 * 10.0 / SPEED_OF_LIGHT_KM_S
        assert delta["doppler_shift_hz"] == pytest.approx(expected)

    def test_get_summary(self):
        summary = DopplerModel({"enabled": True}).get_summary()
        assert summary["enabled"] is True
        assert summary["carrier_freq_hz"] == CARRIER_FREQ_HZ

    def test_registered(self):
        assert "doppler" in STRATEGIES
        assert STRATEGIES["doppler"] is DopplerModel


class TestDopplerWeightOverrides:
    def test_disabled_no_overrides(self):
        model = DopplerModel()
        assert model.get_routing_weight_overrides(_graph(), _node_registry(), 0.0) == {}

    def test_overrides_present_after_links_computed(self):
        model = DopplerModel({"enabled": True})
        graph = _graph()
        registry = _node_registry()
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1010.0, 1.0, 1.0)
        overrides = model.get_routing_weight_overrides(graph, registry, 1.0)
        link = LinkId("a->b")
        shift = CARRIER_FREQ_HZ * 10.0 / SPEED_OF_LIGHT_KM_S
        assert overrides[link] == pytest.approx(abs(shift) / CARRIER_FREQ_HZ)
        assert overrides[link] > 0.0

    def test_zero_shift_links_override_zero(self):
        model = DopplerModel({"enabled": True})
        graph = _graph()
        model.compute_link_physics(NodeId("a"), NodeId("b"), 1000.0, 0.0, 1.0)
        overrides = model.get_routing_weight_overrides(graph, _node_registry(), 0.0)
        assert overrides[LinkId("a->b")] == pytest.approx(0.0)
