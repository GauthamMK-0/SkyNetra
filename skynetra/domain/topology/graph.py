"""
Domain layer (L1) — directed topology graph builder.

`build_topology_graph` assembles the full network inventory — satellites,
compute pods, and ground stations — into a directed NetworkX graph whose
edge and node attribute schemas are defined here at Layer 1.

The attribute slots exist as DATA SLOTS even though only Layer 2 physics
engines populate non-default values. Layer 1 owns the schema; Layer 2
owns the computation. Layer 2 physics engines pass computed numbers DOWN
into Layer 1 pure functions (`compute_isl_link_quality`) as plain dicts
(`link_quality_overrides` keyed by `LinkId`), never as imported classes.

Edge schema (all edges):
    capacity, propagation_delay_ms, thermal_noise_factor,
    radiation_bit_error_rate, effective_capacity_fraction,
    doppler_shift_hz
Node schema (all nodes):
    position, node_type, temperature_k, radiation_dose_rad,
    power_available_w, fault_probability

Graph topology produced:
    * ISL edges: every pair in `isl_links`, added in BOTH directions.
    * GSL edges: satellite <-> ground station, both directions, only when
      the satellite's elevation at the station is >= `gsl_elevation_min_deg`.
    * Pod nodes: added as compute endpoints with the full node schema but
      no incident edges (attachment policy is a Layer 2 routing concern).

May import from: itself, domain, foundation.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from skynetra.domain.topology.isl import (
    compute_gsl_elevation_deg,
    compute_isl_link_quality,
)
from skynetra.foundation.types import LinkId, NodeId, Vector3

DEFAULT_CAPACITY_GBPS = 100.0
DEFAULT_GSL_CAPACITY_GBPS = 10.0
DEFAULT_GSL_ELEVATION_MIN_DEG = 10.0

DEFAULT_NODE_ATTRIBUTES: dict[str, float] = {
    "temperature_k": 293.15,
    "radiation_dose_rad": 0.0,
    "power_available_w": 1000.0,
    "fault_probability": 0.0,
}

NODE_SCHEMA = ("position", "node_type") + tuple(DEFAULT_NODE_ATTRIBUTES.keys())
EDGE_SCHEMA = (
    "capacity",
    "propagation_delay_ms",
    "thermal_noise_factor",
    "radiation_bit_error_rate",
    "effective_capacity_fraction",
    "doppler_shift_hz",
)


def _default_edge_attributes(
    pos_a: Vector3, pos_b: Vector3, capacity_gbps: float
) -> dict[str, Any]:
    distance_km = math.dist(pos_a, pos_b)
    quality = compute_isl_link_quality(pos_a, pos_b, distance_km)
    quality["capacity"] = capacity_gbps
    return quality


def _add_node(graph: nx.DiGraph, nid: NodeId, position: Vector3, node_type: str) -> None:
    graph.add_node(
        nid,
        position=position,
        node_type=node_type,
        **DEFAULT_NODE_ATTRIBUTES,
    )


def build_topology_graph(
    sat_positions: dict[NodeId, Vector3],
    isl_links: list[tuple[NodeId, NodeId]],
    pod_ids: list[NodeId],
    ground_stations: dict[NodeId, Vector3],
    link_capacity_gbps: float = DEFAULT_CAPACITY_GBPS,
    gsl_capacity_gbps: float = DEFAULT_GSL_CAPACITY_GBPS,
    gsl_elevation_min_deg: float = DEFAULT_GSL_ELEVATION_MIN_DEG,
    link_quality_overrides: dict[LinkId, dict[str, Any]] | None = None,
) -> nx.DiGraph:
    """Build the directed network graph from constellation topology inputs.

    Args:
        sat_positions: ECI positions (km) of every satellite node.
        isl_links: Pairs of satellite ids that share an inter-satellite
            link; each pair is added in both directions.
        pod_ids: Compute-pod node ids to include in the graph.
        ground_stations: Ground station ids mapped to ECI positions (km).
        link_capacity_gbps: Nominal ISL capacity for every edge, Gbps.
        gsl_capacity_gbps: Nominal ground-station access link capacity,
            Gbps. Pod attachment links use this class too.
        gsl_elevation_min_deg: Minimum elevation (deg) for a satellite
            <-> ground station edge to exist.
        link_quality_overrides: Optional per-`LinkId` attribute dicts
            computed by Layer 2 physics engines; merged over the default
            edge schema for the matching directed edge only.

    Returns:
        A `networkx.DiGraph` carrying the Layer 1 edge/node schema.
    """
    graph = nx.DiGraph()

    for sat_id, pos in sat_positions.items():
        _add_node(graph, sat_id, pos, "sat")

    for pod_id in pod_ids:
        _add_node(graph, pod_id, (0.0, 0.0, 0.0), "pod")

    for gs_id, pos in ground_stations.items():
        _add_node(graph, gs_id, pos, "ground")

    for sat_a, sat_b in isl_links:
        if sat_a not in sat_positions or sat_b not in sat_positions:
            continue
        graph.add_edge(
            sat_a,
            sat_b,
            **_default_edge_attributes(
                sat_positions[sat_a], sat_positions[sat_b], link_capacity_gbps
            ),
        )
        graph.add_edge(
            sat_b,
            sat_a,
            **_default_edge_attributes(
                sat_positions[sat_b], sat_positions[sat_a], link_capacity_gbps
            ),
        )

    for gs_id, gs_pos in ground_stations.items():
        for sat_id, sat_pos in sat_positions.items():
            if compute_gsl_elevation_deg(sat_pos, gs_pos) < gsl_elevation_min_deg:
                continue
            graph.add_edge(
                sat_id,
                gs_id,
                **_default_edge_attributes(sat_pos, gs_pos, gsl_capacity_gbps),
            )
            graph.add_edge(
                gs_id,
                sat_id,
                **_default_edge_attributes(gs_pos, sat_pos, gsl_capacity_gbps),
            )

    if link_quality_overrides:
        for link_id, overrides in link_quality_overrides.items():
            src, dst = str(link_id).split("->", 1)
            if graph.has_edge(src, dst):
                graph.edges[src, dst].update(overrides)

    return graph
