"""Integration: full 300s simulation, shortest_path, built-in workloads.

Drives the whole stack through the Layer 4 config -> Layer 3 spec ->
engine path, exactly like `orbitdc run` does.
"""

from __future__ import annotations

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation


def _base_config() -> FullConfig:
    return FullConfig(
        simulation={"duration_s": 300.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6},
        pods={"n_pods": 2},
        ground_stations={"n_ground_stations": 2},
        routing={"strategy": "shortest_path"},
    )


def test_full_sim_shortest_path() -> None:
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(_base_config())).run()

    assert results.duration == 300.0

    for name in ("network_metrics", "compute_metrics", "topology_metrics"):
        assert name in results.engine_metrics, f"missing {name}"

    net = results.engine_metrics["network_metrics"]
    assert net["delivered"] > 0
    assert net["drop_rate"] < 0.5
    assert net["avg_latency_s"] > 0
    assert net["avg_latency_s"] * 1000.0 > 0  # mean e2e latency (ms) > 0


def test_full_sim_shortest_path_is_deterministic() -> None:
    first = OrbitDCSimulation.from_spec(config_to_simulation_spec(_base_config())).run()
    second = OrbitDCSimulation.from_spec(config_to_simulation_spec(_base_config())).run()
    assert first.engine_metrics == second.engine_metrics
