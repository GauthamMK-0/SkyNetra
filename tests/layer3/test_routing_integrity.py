"""
L3 integration — routing integrity after Phase 1-3 link dynamics.

Covers three fixes that real queueing dynamics exposed:
- `_isl_links` must not create self-loops for single-plane constellations.
- Shortest-path routing must never transit a pod (pods are endpoints).
- Backpressure must deliver under load without dropping into rings or
  useless pod-transit picks.
"""

from __future__ import annotations

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import PacketDropEvent


def _run(
    n_planes: int,
    sats_per_plane: int,
    n_pods: int,
    strategy: str,
    duration_s: float = 120.0,
) -> OrbitDCSimulation:
    config = FullConfig(
        simulation={"duration_s": duration_s, "seed": 42},
        constellation={"n_planes": n_planes, "sats_per_plane": sats_per_plane},
        pods={"n_pods": n_pods},
        routing={"strategy": strategy},
    )
    return OrbitDCSimulation.from_spec(config_to_simulation_spec(config))


class TestNoSelfLoops:
    def test_single_plane_constellation_has_no_self_loops(self):
        sim = _run(1, 2, 1, "shortest_path")
        sim.setup()
        graph = sim._context.graph
        assert not [(a, b) for a, b in graph.edges if a == b]


class TestShortestPathPodEndpoint:
    def test_no_pod_transit_drops(self):
        results = _run(3, 6, 2, "shortest_path").run()
        reasons = [
            getattr(e, "reason", "")
            for e in results.events
            if isinstance(e, PacketDropEvent)
        ]
        assert "pod_not_transit" not in reasons
        assert results.engine_metrics["network_metrics"]["delivered"] > 0


class TestBackpressureDelivers:
    def test_light_load_matches_shortest_path(self):
        bp = _run(3, 6, 2, "backpressure").run()
        sp = _run(3, 6, 2, "shortest_path").run()
        assert (
            bp.engine_metrics["network_metrics"]["delivered"]
            == sp.engine_metrics["network_metrics"]["delivered"]
        )

    def test_heavy_load_delivers_without_pod_transit(self):
        results = _run(6, 6, 4, "backpressure").run()
        net = results.engine_metrics["network_metrics"]
        assert net["delivered"] > 0
        reasons = [
            getattr(e, "reason", "")
            for e in results.events
            if isinstance(e, PacketDropEvent)
        ]
        assert "pod_not_transit" not in reasons

    def test_deterministic(self):
        first = _run(3, 6, 2, "backpressure").run()
        second = _run(3, 6, 2, "backpressure").run()
        assert (
            first.engine_metrics["network_metrics"]["delivered"]
            == second.engine_metrics["network_metrics"]["delivered"]
        )
