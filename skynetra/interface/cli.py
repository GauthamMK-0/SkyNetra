"""
Interface layer (L4) — SkyNetra Click CLI.

Explicit command set (no auto-discovery): run, sweep, gen-config,
list-strategies, compare.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

import click

from skynetra.engines.physics.registry import STRATEGIES as PHYSICS_STRATEGIES
from skynetra.engines.routing.registry import STRATEGIES as ROUTING_STRATEGIES
from skynetra.engines.workload.registry import STRATEGIES as WORKLOAD_STRATEGIES
from skynetra.foundation.logging_setup import configure_logging
from skynetra.interface.config.defaults import (
    config_to_simulation_spec,
    get_physics_enabled_config,
    load_config,
    save_config,
)
from skynetra.interface.config.schema import FullConfig
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.metrics.registry import STRATEGIES as METRICS_STRATEGIES

SUMMARY_KEYS = (
    "delivered",
    "dropped",
    "transmitted",
    "avg_latency_s",
    "drop_rate",
    "compute_jobs_completed",
)


def _enable_physics(config: FullConfig) -> FullConfig:
    for section in (
        config.physics.thermal,
        config.physics.radiation,
        config.physics.power,
    ):
        section["enabled"] = True
    return config


def _load_base_config(path: Optional[str], physics: bool) -> FullConfig:
    if path is not None:
        config = load_config(path)
    else:
        config = get_physics_enabled_config() if physics else FullConfig()
    if path is not None and physics:
        _enable_physics(config)
    return config


def _write_results(results: Any, output: Path, filename: str) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    target = output / filename
    with open(target, "w") as f:
        json.dump(results.to_dict(), f, indent=2)
    return target


def _echo_summary(results: Any) -> None:
    click.echo(f"Simulation complete: duration_s={results.duration:.1f}")
    net = results.engine_metrics.get("network_metrics", {})
    if net:
        click.echo(
            "network: "
            f"delivered={net.get('delivered', 0)}, "
            f"dropped={net.get('dropped', 0)}, "
            f"avg_latency_s={net.get('avg_latency_s', 0.0):.6f}"
        )


@click.group()
def main() -> None:
    """SkyNetra: Space Data Center Network Simulator"""
    configure_logging(level="INFO")


@main.command()
@click.option("--config", "-c", default=None, help="Path to config YAML/JSON")
@click.option(
    "--routing",
    "-r",
    type=click.Choice(["shortest_path", "backpressure"], case_sensitive=False),
    default=None,
    help="Routing strategy override",
)
@click.option("--duration", "-d", default=None, type=float, help="Simulation duration (s)")
@click.option("--output", "-o", default="results/", help="Output directory")
@click.option("--seed", default=None, type=int, help="RNG seed")
@click.option("--physics/--no-physics", default=False, help="Enable physics models")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run(
    config: Optional[str],
    routing: Optional[str],
    duration: Optional[float],
    output: str,
    seed: Optional[int],
    physics: bool,
    verbose: bool,
) -> None:
    """Run a single OrbitDC simulation"""
    cfg = _load_base_config(config, physics)
    if routing is not None:
        cfg.routing.strategy = routing  # type: ignore[assignment]
    if duration is not None:
        cfg.simulation.duration_s = duration
    if seed is not None:
        cfg.simulation.seed = seed

    spec = config_to_simulation_spec(cfg)
    if verbose:
        click.echo(
            f"Running: {spec.routing_strategy} "
            f"({spec.sim_duration_s}s, {spec.constellation.total_satellites} sats)"
        )
    results = OrbitDCSimulation.from_spec(spec).run()
    target = _write_results(results, Path(output), "sim_results.json")
    _echo_summary(results)
    click.echo(f"Results written to {target}")


@main.command()
@click.option("--config", "-c", default=None, help="Path to config YAML/JSON")
@click.option("--output", "-o", default="results/sweep/", help="Output directory")
@click.option("--physics/--no-physics", default=False, help="Enable physics models")
def sweep(config: Optional[str], output: str, physics: bool) -> None:
    """Run the full scaling sweep experiment"""
    cfg = _load_base_config(config, physics)
    scales = [(2, 3), (3, 4), (4, 5)]
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for n_planes, sats_per_plane in scales:
        for n_pods in (1, 2):
            cfg.constellation.n_planes = n_planes
            cfg.constellation.sats_per_plane = sats_per_plane
            cfg.pods.n_pods = n_pods
            spec = config_to_simulation_spec(cfg)
            results = OrbitDCSimulation.from_spec(spec).run()
            net = results.engine_metrics.get("network_metrics", {})
            name = f"sweep_p{n_planes}x{sats_per_plane}_pods{n_pods}"
            _write_results(results, out_dir, f"{name}.json")
            rows.append(
                {
                    "name": name,
                    "n_planes": n_planes,
                    "sats_per_plane": sats_per_plane,
                    "n_pods": n_pods,
                    "duration_s": round(results.duration, 3),
                    "delivered": net.get("delivered", 0),
                    "dropped": net.get("dropped", 0),
                    "avg_latency_s": net.get("avg_latency_s", 0.0),
                }
            )
            click.echo(f"Finished {name}")
    with open(out_dir / "summary.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    click.echo(f"Sweep complete: {len(rows)} runs, summary at {out_dir / 'summary.csv'}")


@main.command()
@click.option("--physics/--no-physics", default=False, help="Enable physics models")
@click.option("--output", "-o", default="skynetra_config.yaml", help="Output config path")
def gen_config(physics: bool, output: str) -> None:
    """Generate a config YAML file"""
    cfg = get_physics_enabled_config() if physics else FullConfig()
    save_config(cfg, output)
    click.echo(f"Config written to {output}")


@main.command()
def list_strategies() -> None:
    """List all statically registered strategies across layer2/layer3
    registries: routing, physics, workload, metrics — read directly
    from each registry.py STRATEGIES dict."""
    click.echo("Routing:")
    for name in sorted(ROUTING_STRATEGIES):
        click.echo(f"  {name}")
    click.echo("Physics:")
    for name in sorted(PHYSICS_STRATEGIES):
        click.echo(f"  {name}")
    click.echo("Workload:")
    for name in sorted(WORKLOAD_STRATEGIES):
        click.echo(f"  {name}")
    click.echo("Metrics:")
    for name in sorted(METRICS_STRATEGIES):
        click.echo(f"  {name}")


@main.command()
@click.option("--config", "-c", default=None, help="Path to config YAML/JSON")
@click.option("--output", "-o", default="results/compare/", help="Output directory")
def compare(config: Optional[str], output: str) -> None:
    """Run SP vs BP head-to-head and print comparison"""
    cfg = _load_base_config(config, False)
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}
    for strategy in ("shortest_path", "backpressure"):
        cfg.routing.strategy = strategy
        spec = config_to_simulation_spec(cfg)
        results[strategy] = OrbitDCSimulation.from_spec(spec).run()
        _write_results(results[strategy], out_dir, f"compare_{strategy}.json")

    sp_net = results["shortest_path"].engine_metrics.get("network_metrics", {})
    bp_net = results["backpressure"].engine_metrics.get("network_metrics", {})
    click.echo(f"{'metric':<24} {'shortest_path':>14} {'backpressure':>14}")
    for key in SUMMARY_KEYS:
        click.echo(f"{key:<24} {sp_net.get(key, 0):>14} {bp_net.get(key, 0):>14}")
    click.echo(f"Comparison written to {out_dir}")
