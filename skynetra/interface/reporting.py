"""
Interface layer (L4) — results export and comparison utilities.

Plain functions over `SimulationResults`, consistent with the viz
modules: no strategy abstraction is needed because exporting and
comparison are fixed, deterministic projections of the results object.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

from skynetra.interface.viz.network_plots import (
    latency_cdf_plot,
    link_utilization_heatmap,
    throughput_plot,
)
from skynetra.interface.viz.physics_plots import (
    physics_vs_network_impact,
    power_state_timeseries,
    radiation_dose_accumulation,
    temperature_timeseries,
)
from skynetra.orchestration.results import SimulationResults

_PLOT_FUNCTIONS = [
    latency_cdf_plot,
    throughput_plot,
    link_utilization_heatmap,
    temperature_timeseries,
    radiation_dose_accumulation,
    power_state_timeseries,
    physics_vs_network_impact,
]


def _cell(value: object) -> object:
    if isinstance(value, (list, dict)):
        return ""
    return value


def export_results_csv(results: SimulationResults, path: str) -> None:
    """Write one CSV row per metrics collector (flattened summaries)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    metric_keys = sorted({key for summary in results.engine_metrics.values() for key in summary})
    with open(p, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["collector"] + metric_keys)
        for name in sorted(results.engine_metrics):
            summary = results.engine_metrics[name]
            writer.writerow([name] + [_cell(summary.get(key)) for key in metric_keys])


def export_results_json(results: SimulationResults, path: str) -> None:
    """Write the full results object as JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(results.to_dict(), f, indent=2)


def print_comparison_table(a: SimulationResults, b: SimulationResults) -> None:
    """Print an aligned side-by-side metric comparison of two runs."""
    collectors = sorted(set(a.engine_metrics) | set(b.engine_metrics))
    print(f"{'collector':<22}{'metric':<26}{'a':>12}{'b':>12}")
    print("-" * 72)
    for name in collectors:
        summary_a = a.engine_metrics.get(name, {})
        summary_b = b.engine_metrics.get(name, {})
        for metric in sorted(set(summary_a) | set(summary_b)):
            print(
                f"{name:<22}{metric:<26}{str(_cell(summary_a.get(metric))):>12}"
                f"{str(_cell(summary_b.get(metric))):>12}"
            )


def save_all_plots(results: SimulationResults, output_dir: str) -> None:
    """Render every single-run viz plot to `output_dir/{name}.png`.

    The scaling plots (multi-run aggregates) and the orbit/ISL plot
    (needs a live context snapshot) are intentionally excluded — they
    take inputs a single `SimulationResults` object cannot provide.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for plot_fn in _PLOT_FUNCTIONS:
        fig = plot_fn(results)
        fig.savefig(out / f"{plot_fn.__name__}.png")
        plt.close(fig)
