"""
L3 tests — Earth rotation + GSL elevation gating (Phase 3).

Ground stations (and pods, modeled as ground-like facilities) are
Earth-fixed: their inertial positions rotate with the sidereal rate.
GSL edges appear/disappear as elevation crosses the configured mask.

Topology: 1 plane x 2 sats, 550 km. Empirically verified behavior with
mask 10 deg: GS edges exist at t=0 and t=3000 (sat overhead), vanish
elsewhere; at t=3000 a 45 deg mask removes them entirely.
"""

from __future__ import annotations

import math

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import ReferenceCircularPropagator
from skynetra.engines.routing.registry import get_routing_engine
from skynetra.foundation.types import NodeId
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import TopologyUpdateEvent

CONSTELLATION_1X2 = ConstellationConfig(
    n_planes=1, sats_per_plane=2, altitude_km=550, inclination_deg=55
)

GS_1 = NodeId("gs-1")


def _registry() -> dict[NodeId, Node]:
    propagator = ReferenceCircularPropagator()
    registry: dict[NodeId, Node] = {
        sat_id: RelayNode(sat_id) for sat_id in propagator.get_sat_ids(CONSTELLATION_1X2)
    }
    registry[NodeId("pod-1")] = PodNode(NodeId("pod-1"))
    registry[GS_1] = GroundStationNode(GS_1)
    return registry


def _sim(gsl_elevation_min_deg: float = 10.0, **kwargs: object) -> OrbitDCSimulation:
    return OrbitDCSimulation.from_layers(
        constellation=CONSTELLATION_1X2,
        node_registry=_registry(),
        routing_engine=get_routing_engine("shortest_path"),
        gsl_elevation_min_deg=gsl_elevation_min_deg,
        **kwargs,
    )


def _gs_edges(sim: OrbitDCSimulation, time_s: float) -> int:
    sim.setup()
    graph = sim._build_graph(_registry(), time_s)
    return sum(1 for a, b in graph.edges if "gs" in str(a) or "gs" in str(b))


class TestEarthRotation:
    def test_station_positions_rotate_over_time(self):
        sim = _sim()
        sim.setup()
        pos_0 = sim._build_graph(_registry(), 0.0).nodes[GS_1]["position"]
        pos_3000 = sim._build_graph(_registry(), 3000.0).nodes[GS_1]["position"]
        assert pos_0 != pos_3000
        # Rotation preserves the radius (Earth surface).
        for pos in (pos_0, pos_3000):
            norm = math.sqrt(sum(c * c for c in pos))
            assert norm == pytest.approx(6371.0, abs=1e-6)

    def test_topology_edge_count_varies_with_rotation(self):
        results = _sim(
            sim_duration_s=7200.0, topology_update_interval_s=600.0
        ).run()
        edge_counts = {
            ev.edge_count
            for ev in results.events
            if isinstance(ev, TopologyUpdateEvent)
        }
        assert len(edge_counts) > 1, "GS edges should appear/disappear as Earth rotates"


class TestElevationMask:
    def test_strict_mask_reduces_gs_edges(self):
        permissive = _gs_edges(_sim(10.0), 3000.0)
        strict = _gs_edges(_sim(45.0), 3000.0)
        assert permissive > strict
        assert strict == 0

    def test_low_mask_keeps_overhead_edge(self):
        # At t=0 sat-0-0 is directly overhead (elevation ~90 deg): any
        # mask up to 90 keeps the edge.
        assert _gs_edges(_sim(10.0), 0.0) == 2
        assert _gs_edges(_sim(85.0), 0.0) == 2

    def test_config_translation_preserves_elevation_mask(self):
        config = FullConfig(ground_stations={"gsl_elevation_min_deg": 30.0})
        spec = config_to_simulation_spec(config)
        assert spec.gsl_elevation_min_deg == 30.0

    def test_mask_threads_into_engine(self):
        sim = OrbitDCSimulation.from_spec(
            config_to_simulation_spec(
                FullConfig(ground_stations={"gsl_elevation_min_deg": 45.0})
            )
        )
        assert sim._gsl_elevation_min_deg == 45.0
