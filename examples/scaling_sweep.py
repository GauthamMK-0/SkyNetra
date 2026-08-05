"""
Full scaling sweep for OrbitDC: runs every (constellation size, pod
count, routing strategy, physics mode) combination N_RUNS times at
SIM_DURATION and aggregates mean +/- std.

Each config is expressed as a Layer 4 `FullConfig`, translated with
`config_to_simulation_spec`, and executed via
`OrbitDCSimulation.from_spec(spec).run()` — the L4 -> L3 -> L2/L1/L0
path end to end, exactly as the `orbitdc run` CLI does.

Outputs under results/:
    scaling_sweep_results.csv      one row per config (mean/std per metric)
    scaling_sweep_summary.json     machine-readable copy of the same data
    latency_vs_constellation_size.png / throughput_vs_num_pods.png /
    drop_rate_vs_load.png / physics_impact_vs_scale.png
    (figures rendered from the aggregated means via the L4 scaling plots)
plus a printed SP-vs-BP comparison table.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.interface.viz.scaling_plots import (
    drop_rate_vs_load,
    latency_vs_constellation_size,
    physics_impact_vs_scale,
    throughput_vs_num_pods,
)
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.results import SimulationResults

CONSTELLATION_SIZES = [(3, 6), (6, 6), (6, 10), (10, 10)]
NUM_PODS_OPTIONS = [2, 4, 8, 16]
ROUTING_STRATEGIES = ["shortest_path", "backpressure"]
PHYSICS_MODES = ["disabled", "thermal_only", "full_physics"]
N_RUNS = 3
SIM_DURATION = 1800.0
BASE_SEED = 42

RESULTS_DIR = Path("results")

METRIC_KEYS = ("delivered", "dropped", "transmitted", "avg_latency_s", "drop_rate")


def apply_physics_mode(cfg: FullConfig, mode: str) -> None:
    """Enable physics sections and their collector for a physics mode."""
    if mode == "disabled":
        return
    if mode in ("thermal_only", "full_physics"):
        cfg.physics.thermal["enabled"] = True
    if mode == "full_physics":
        cfg.physics.radiation["enabled"] = True
        cfg.physics.power["enabled"] = True
    if "physics_metrics" not in cfg.metrics.active:
        cfg.metrics.active.append("physics_metrics")


def run_config(cfg: FullConfig) -> dict[str, float]:
    """Run one simulation for `cfg` and return headline metrics."""
    spec = config_to_simulation_spec(cfg)
    results = OrbitDCSimulation.from_spec(spec).run()
    net = results.engine_metrics["network_metrics"]
    stats = {key: float(net[key]) for key in METRIC_KEYS}
    stats["physics_caused_drops"] = float(
        results.engine_metrics.get("physics_metrics", {}).get("physics_caused_drops", 0.0)
    )
    return stats


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    return (mean(values), stdev(values) if len(values) > 1 else 0.0)


def synthetic_results(row: dict[str, Any]) -> SimulationResults:
    """SimulationResults carrying a config row's aggregated means, so the
    scaling plots can project the sweep without re-running."""
    engine_metrics: dict[str, Any] = {
        "network_metrics": {key: row[f"{key}_mean"] for key in METRIC_KEYS},
        "topology_metrics": {"final_node_count": row["constellation_size"]},
        "compute_metrics": {"jobs_by_pod": {f"pod-{i}": 0 for i in range(row["num_pods"])}},
    }
    if row["physics_mode"] != "disabled":
        engine_metrics["physics_metrics"] = {
            "physics_caused_drops": row["physics_caused_drops_mean"]
        }
    return SimulationResults(engine_metrics=engine_metrics, events=[], duration=SIM_DURATION)


def save_figure(fig: plt.Figure, name: str) -> None:
    fig.savefig(RESULTS_DIR / name)
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []

    for n_planes, sats_per_plane in CONSTELLATION_SIZES:
        for num_pods in NUM_PODS_OPTIONS:
            for routing in ROUTING_STRATEGIES:
                for physics_mode in PHYSICS_MODES:
                    cfg = FullConfig(
                        simulation={"duration_s": SIM_DURATION, "seed": BASE_SEED},
                        constellation={
                            "n_planes": n_planes,
                            "sats_per_plane": sats_per_plane,
                        },
                        pods={"n_pods": num_pods},
                        routing={"strategy": routing},
                    )
                    apply_physics_mode(cfg, physics_mode)
                    per_run = []
                    for run_index in range(N_RUNS):
                        cfg.simulation.seed = BASE_SEED + run_index
                        per_run.append(run_config(cfg))

                    row: dict[str, Any] = {
                        "n_planes": n_planes,
                        "sats_per_plane": sats_per_plane,
                        "constellation_size": n_planes * sats_per_plane,
                        "num_pods": num_pods,
                        "routing": routing,
                        "physics_mode": physics_mode,
                        "n_runs": N_RUNS,
                    }
                    for key in per_run[0]:
                        values = [run[key] for run in per_run]
                        row[f"{key}_mean"], row[f"{key}_std"] = mean_std(values)
                    rows.append(row)
                    print(
                        f"done: {n_planes}x{sats_per_plane} sats, {num_pods} pods, "
                        f"{routing}, {physics_mode}"
                    )

    _write_csv(rows)
    _write_json(rows)
    _write_figures(rows)
    _print_comparison_table(rows)


def _write_csv(rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "n_planes",
        "sats_per_plane",
        "constellation_size",
        "num_pods",
        "routing",
        "physics_mode",
        "n_runs",
    ] + [
        f"{key}_{suffix}"
        for key in (*METRIC_KEYS, "physics_caused_drops")
        for suffix in ("mean", "std")
    ]
    with open(RESULTS_DIR / "scaling_sweep_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {RESULTS_DIR / 'scaling_sweep_results.csv'} ({len(rows)} rows)")


def _write_json(rows: list[dict[str, Any]]) -> None:
    payload = {
        "config": {
            "constellation_sizes": [list(size) for size in CONSTELLATION_SIZES],
            "num_pods_options": NUM_PODS_OPTIONS,
            "routing_strategies": ROUTING_STRATEGIES,
            "physics_modes": PHYSICS_MODES,
            "n_runs": N_RUNS,
            "sim_duration_s": SIM_DURATION,
            "base_seed": BASE_SEED,
        },
        "results": rows,
    }
    path = RESULTS_DIR / "scaling_sweep_summary.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote {path}")


def _write_figures(rows: list[dict[str, Any]]) -> None:
    def subset(routing: str, physics_mode: str) -> list[dict[str, Any]]:
        return [r for r in rows if r["routing"] == routing and r["physics_mode"] == physics_mode]

    sp_disabled = subset("shortest_path", "disabled")
    save_figure(
        latency_vs_constellation_size(
            [synthetic_results(r) for r in sp_disabled if r["num_pods"] == NUM_PODS_OPTIONS[0]]
        ),
        "latency_vs_constellation_size.png",
    )
    save_figure(
        throughput_vs_num_pods(
            [synthetic_results(r) for r in sp_disabled if r["constellation_size"] == 18]
        ),
        "throughput_vs_num_pods.png",
    )
    save_figure(
        drop_rate_vs_load([synthetic_results(r) for r in sp_disabled]),
        "drop_rate_vs_load.png",
    )
    physics_rows = [
        r
        for r in rows
        if r["routing"] == "shortest_path"
        and r["physics_mode"] in ("thermal_only", "full_physics")
        and r["num_pods"] == NUM_PODS_OPTIONS[0]
    ]
    save_figure(
        physics_impact_vs_scale([synthetic_results(r) for r in physics_rows]),
        "physics_impact_vs_scale.png",
    )


def _print_comparison_table(rows: list[dict[str, Any]]) -> None:
    print("\nSP vs BP comparison (delivered / avg latency / drop rate):")
    header = (
        f"{'size':>6} {'pods':>4} {'physics':<13} "
        f"{'SP deliv':>9} {'BP deliv':>9} {'SP lat':>9} {'BP lat':>9} "
        f"{'SP drop':>8} {'BP drop':>8}"
    )
    print(header)
    print("-" * len(header))
    for n_planes, sats_per_plane in CONSTELLATION_SIZES:
        for num_pods in NUM_PODS_OPTIONS:
            for physics_mode in PHYSICS_MODES:

                def pick(routing: str) -> dict[str, Any]:
                    return next(
                        r
                        for r in rows
                        if r["n_planes"] == n_planes
                        and r["sats_per_plane"] == sats_per_plane
                        and r["num_pods"] == num_pods
                        and r["physics_mode"] == physics_mode
                        and r["routing"] == routing
                    )

                sp = pick("shortest_path")
                bp = pick("backpressure")
                print(
                    f"{sp['constellation_size']:>6} {num_pods:>4} {physics_mode:<13} "
                    f"{sp['delivered_mean']:>9.1f} {bp['delivered_mean']:>9.1f} "
                    f"{sp['avg_latency_s_mean']:>9.4f} {bp['avg_latency_s_mean']:>9.4f} "
                    f"{sp['drop_rate_mean']:>8.3f} {bp['drop_rate_mean']:>8.3f}"
                )


if __name__ == "__main__":
    main()
