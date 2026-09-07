"""
Tests for high-level simulation runner API (skynetra.simulate) and
intelligent SimulationResults accessors and plotting.
"""

from __future__ import annotations

from pathlib import Path

import skynetra as sn
from skynetra.orchestration.results import SimulationResults


def test_simulate_default_execution() -> None:
    results = sn.simulate(duration_s=10.0, pods=2, seed=42)
    assert isinstance(results, SimulationResults)
    assert results.duration == 10.0

    # Verify typed accessors
    assert results.network.transmitted > 0
    assert results.network.delivered >= 0
    assert results.network.avg_latency_ms >= 0.0
    assert 0.0 <= results.network.delivery_rate <= 100.0

    assert results.compute.jobs_completed >= 0
    assert results.compute.total_flops >= 0.0
    assert results.compute.avg_service_time_ms >= 0.0

    assert results.physics.avg_temperature_k > 0.0
    assert isinstance(results.physics.active_models, list)

    assert results.topology.topology_updates >= 0


def test_simulate_string_constellation_and_training() -> None:
    results = sn.simulate(
        duration_s=15.0,
        constellation="2x3",
        pods=2,
        routing="shortest_path",
        workload="training",
        physics=True,
    )
    assert results.duration == 15.0
    assert results.network.transmitted > 0


def test_simulate_federated_learning() -> None:
    results = sn.simulate(
        duration_s=30.0,
        constellation=(2, 3),
        pods=2,
        workload="federated",
        fl_rounds=1,
        fl_interval_s=10.0,
    )
    assert results.duration == 30.0


def test_results_report_formatting() -> None:
    results = sn.simulate(duration_s=10.0, pods=1)
    report_text = results.report()
    assert "SKYNETRA SIMULATION EXECUTION REPORT" in report_text
    assert "Network Forwarding & Delivery" in report_text
    assert "On-Orbit Compute Data Center Servicing" in report_text


def test_results_plot_export(tmp_path: Path) -> None:
    results = sn.simulate(duration_s=10.0, pods=1)
    plot_paths = results.plot(output_dir=tmp_path)
    assert len(plot_paths) == 7
    for path in plot_paths:
        assert path.exists()
        assert path.suffix == ".png"
