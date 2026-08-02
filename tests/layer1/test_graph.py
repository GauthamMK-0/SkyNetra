from __future__ import annotations

import networkx as nx
import pytest

from skynetra.domain.topology.graph import build_topology_graph
from skynetra.domain.topology.isl import SPEED_OF_LIGHT_KM_S
from skynetra.foundation.types import LinkId, NodeId, Vector3

SAT_POSITIONS: dict[NodeId, Vector3] = {
    NodeId("sat-0-0"): (6921.0, 0.0, 0.0),
    NodeId("sat-0-1"): (6921.0, 100.0, 0.0),
}
ISL_LINKS: list[tuple[NodeId, NodeId]] = [(NodeId("sat-0-0"), NodeId("sat-0-1"))]
POD_IDS: list[NodeId] = [NodeId("pod-1")]
GROUND_STATIONS: dict[NodeId, Vector3] = {
    NodeId("gs-1"): (6371.0, 0.0, 0.0),
}


def _build(**kwargs) -> nx.DiGraph:
    params: dict = {
        "sat_positions": SAT_POSITIONS,
        "isl_links": ISL_LINKS,
        "pod_ids": POD_IDS,
        "ground_stations": GROUND_STATIONS,
    }
    params.update(kwargs)
    return build_topology_graph(**params)


def _delay_ms(distance_km: float) -> float:
    return distance_km * 1000.0 / SPEED_OF_LIGHT_KM_S


class TestGraphStructure:
    def test_returns_directed_graph(self):
        graph = _build()
        assert isinstance(graph, nx.DiGraph)
        assert not graph.is_multigraph()

    def test_all_node_kinds_present(self):
        graph = _build()
        assert set(graph.nodes()) == {
            NodeId("sat-0-0"),
            NodeId("sat-0-1"),
            NodeId("pod-1"),
            NodeId("gs-1"),
        }

    def test_isl_edges_are_bidirectional(self):
        graph = _build()
        assert graph.has_edge(NodeId("sat-0-0"), NodeId("sat-0-1"))
        assert graph.has_edge(NodeId("sat-0-1"), NodeId("sat-0-0"))

    def test_gsl_edges_overhead_satellite(self):
        graph = _build()
        assert graph.has_edge(NodeId("sat-0-0"), NodeId("gs-1"))
        assert graph.has_edge(NodeId("gs-1"), NodeId("sat-0-0"))

    def test_gsl_elevation_filter(self):
        far_sat = {NodeId("sat-low"): (7000.0, 0.0, 7000.0)}
        graph = build_topology_graph(
            sat_positions=far_sat,
            isl_links=[],
            pod_ids=[],
            ground_stations=GROUND_STATIONS,
            gsl_elevation_min_deg=10.0,
        )
        assert not graph.has_edge(NodeId("sat-low"), NodeId("gs-1"))
        assert not graph.has_edge(NodeId("gs-1"), NodeId("sat-low"))


class TestNodeSchema:
    def test_node_schema_defaults(self):
        graph = _build()
        attrs = graph.nodes[NodeId("sat-0-0")]
        assert attrs["position"] == (6921.0, 0.0, 0.0)
        assert attrs["node_type"] == "sat"
        assert attrs["temperature_k"] == 293.15
        assert attrs["radiation_dose_rad"] == 0.0
        assert attrs["power_available_w"] == 1000.0
        assert attrs["fault_probability"] == 0.0

    def test_node_types(self):
        graph = _build()
        assert graph.nodes[NodeId("sat-0-0")]["node_type"] == "sat"
        assert graph.nodes[NodeId("pod-1")]["node_type"] == "pod"
        assert graph.nodes[NodeId("gs-1")]["node_type"] == "ground"

    def test_pod_node_position_default(self):
        graph = _build()
        assert graph.nodes[NodeId("pod-1")]["position"] == (0.0, 0.0, 0.0)


class TestEdgeSchema:
    def test_edge_schema_defaults(self):
        graph = _build()
        attrs = graph.edges[NodeId("sat-0-0"), NodeId("sat-0-1")]
        assert attrs["capacity"] == 10.0
        assert attrs["propagation_delay_ms"] == pytest.approx(_delay_ms(100.0))
        assert attrs["thermal_noise_factor"] == 1.0
        assert attrs["radiation_bit_error_rate"] == 0.0
        assert attrs["effective_capacity_fraction"] == 1.0
        assert attrs["doppler_shift_hz"] == 0.0

    def test_capacity_param(self):
        graph = _build(link_capacity_gbps=25.0)
        assert graph.edges[NodeId("sat-0-0"), NodeId("sat-0-1")]["capacity"] == 25.0
        assert graph.edges[NodeId("sat-0-0"), NodeId("gs-1")]["capacity"] == 25.0

    def test_gsl_edge_schema(self):
        graph = _build()
        attrs = graph.edges[NodeId("gs-1"), NodeId("sat-0-0")]
        assert attrs["propagation_delay_ms"] == pytest.approx(_delay_ms(550.0))
        assert attrs["capacity"] == 10.0


class TestLinkQualityOverrides:
    def test_override_applied_to_matching_direction_only(self):
        graph = _build(
            link_quality_overrides={
                LinkId("sat-0-0->sat-0-1"): {"doppler_shift_hz": 900.0}
            }
        )
        assert graph.edges[NodeId("sat-0-0"), NodeId("sat-0-1")]["doppler_shift_hz"] == 900.0
        assert graph.edges[NodeId("sat-0-1"), NodeId("sat-0-0")]["doppler_shift_hz"] == 0.0

    def test_override_merges_over_schema(self):
        graph = _build(
            link_quality_overrides={
                LinkId("gs-1->sat-0-0"): {"effective_capacity_fraction": 0.5}
            }
        )
        attrs = graph.edges[NodeId("gs-1"), NodeId("sat-0-0")]
        assert attrs["effective_capacity_fraction"] == 0.5
        assert attrs["capacity"] == 10.0
        assert attrs["propagation_delay_ms"] == pytest.approx(_delay_ms(550.0))

    def test_override_for_unknown_link_ignored(self):
        graph = _build(
            link_quality_overrides={
                LinkId("sat-0-0->pod-1"): {"doppler_shift_hz": 1.0}
            }
        )
        assert not graph.has_edge(NodeId("sat-0-0"), NodeId("pod-1"))

    def test_no_overrides_default(self):
        graph = _build()
        assert graph.edges[NodeId("sat-0-0"), NodeId("sat-0-1")]["doppler_shift_hz"] == 0.0
