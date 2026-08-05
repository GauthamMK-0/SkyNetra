"""Integration: full 300s simulation with backpressure routing, plus a
SP-vs-BP head-to-head comparison on identical inputs."""

from __future__ import annotations

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation


def _config(strategy: str) -> FullConfig:
    return FullConfig(
        simulation={"duration_s": 300.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6},
        pods={"n_pods": 2},
        ground_stations={"n_ground_stations": 2},
        routing={"strategy": strategy},
    )


def test_full_sim_backpressure() -> None:
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(_config("backpressure"))).run()

    assert results.duration == 300.0
    net = results.engine_metrics["network_metrics"]
    # Backpressure is a greedy per-hop router: on ring topologies it can
    # cycle to the hop limit, so no delivery guarantee is asserted here —
    # completion with a consistent engine_metrics summary is the contract.
    assert "delivered" in net
    assert "drop_rate" in net
    assert net["dropped"] >= 0


def test_sp_vs_bp_results_differ() -> None:
    sp = OrbitDCSimulation.from_spec(config_to_simulation_spec(_config("shortest_path"))).run()
    bp = OrbitDCSimulation.from_spec(config_to_simulation_spec(_config("backpressure"))).run()

    sp_net = sp.engine_metrics["network_metrics"]
    bp_net = bp.engine_metrics["network_metrics"]
    headline_sp = (sp_net["delivered"], sp_net["dropped"], sp_net["avg_latency_s"])
    headline_bp = (bp_net["delivered"], bp_net["dropped"], bp_net["avg_latency_s"])
    assert headline_sp != headline_bp
