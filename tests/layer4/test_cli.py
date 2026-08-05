"""Layer 4 CLI tests (Click CliRunner)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from skynetra.interface.cli import main
from skynetra.interface.config.defaults import load_config


def test_run_shortest_path(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--duration", "60", "--routing", "shortest_path", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert "Simulation complete" in result.output
    results = json.loads((tmp_path / "sim_results.json").read_text())
    assert results["duration"] == 60.0


def test_run_backpressure(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--duration", "60", "--routing", "backpressure", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output


def test_run_physics(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--duration", "60", "--physics", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output


def test_run_with_config_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text("simulation:\n  duration_s: 10.0\n  seed: 1\n")
    out_dir = tmp_path / "out"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["run", "--config", str(cfg_path), "--output", str(out_dir)],
    )
    assert result.exit_code == 0, result.output
    results = json.loads((out_dir / "sim_results.json").read_text())
    assert results["duration"] == 10.0


def test_run_invalid_routing_choice(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--routing", "wormhole"])
    assert result.exit_code == 2


def test_gen_config(tmp_path: Path) -> None:
    out = str(tmp_path / "skynetra_config.yaml")
    runner = CliRunner()
    result = runner.invoke(main, ["gen-config", "--output", out])
    assert result.exit_code == 0, result.output
    cfg = load_config(out)
    assert cfg.simulation.duration_s == 60.0
    assert cfg.physics.thermal["enabled"] is False


def test_gen_config_physics(tmp_path: Path) -> None:
    out = str(tmp_path / "physics_config.yaml")
    runner = CliRunner()
    result = runner.invoke(main, ["gen-config", "--physics", "--output", out])
    assert result.exit_code == 0, result.output
    cfg = load_config(out)
    assert cfg.physics.thermal["enabled"] is True
    assert cfg.physics.radiation["enabled"] is True
    assert cfg.physics.power["enabled"] is True


def test_list_strategies() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["list-strategies"])
    assert result.exit_code == 0, result.output
    for name in (
        "shortest_path",
        "backpressure",
        "thermal",
        "radiation",
        "power",
        "doppler",
        "ai_training_sync",
        "inference_query",
        "federated_learning",
        "network_metrics",
        "compute_metrics",
        "topology_metrics",
        "physics_metrics",
    ):
        assert name in result.output


def test_compare(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["compare", "--output", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "compare_shortest_path.json").exists()
    assert (tmp_path / "compare_backpressure.json").exists()
    assert "shortest_path" in result.output
    assert "backpressure" in result.output
    assert "delivered" in result.output


def test_sweep(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["sweep", "--output", str(tmp_path)])
    assert result.exit_code == 0, result.output
    summary = tmp_path / "summary.csv"
    assert summary.exists()
    rows = summary.read_text().strip().splitlines()
    assert len(rows) == 7  # header + 3 scales x 2 pod counts
    assert (tmp_path / "sweep_p2x3_pods1.json").exists()
