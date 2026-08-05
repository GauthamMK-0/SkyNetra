"""
Interface layer (L4) — scaling experiment plots.

Like the other viz modules, every function here is a PLAIN FUNCTION.
Scaling plots aggregate multiple `SimulationResults` objects (one per
sweep point) and project one headline metric against a derived scale
axis — there is no runtime-behavioral variation to abstract behind a
strategy interface; each plot is a fixed, deterministic projection.

Scale axes are derived from each result's own data: constellation size
= distinct satellite node ids seen in events (falling back to the
topology collector's `final_node_count`), pod count = distinct `pod-*`
node ids seen in events (falling back to `compute_metrics.jobs_by_pod`
keys).

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from skynetra.interface.viz._common import empty_figure
from skynetra.orchestration.events import ComputeJobCompleteEvent, PacketEvent
from skynetra.orchestration.results import SimulationResults


def _distinct_node_ids(results: SimulationResults, prefix: str) -> set[str]:
    ids: set[str] = set()
    for ev in results.events:
        if isinstance(ev, PacketEvent):
            ids.add(str(ev.node_id))
            ids.add(str(ev.packet.src))
            ids.add(str(ev.packet.dst))
        if isinstance(ev, ComputeJobCompleteEvent):
            ids.add(str(ev.node_id))
    return {nid for nid in ids if nid.startswith(prefix)}


def _satellite_count(results: SimulationResults) -> int:
    sat_ids = _distinct_node_ids(results, "sat-")
    if sat_ids:
        return len(sat_ids)
    topology = results.engine_metrics.get("topology_metrics", {})
    return int(topology.get("final_node_count", 0))


def _pod_count(results: SimulationResults) -> int:
    pod_ids = _distinct_node_ids(results, "pod-")
    if pod_ids:
        return len(pod_ids)
    compute = results.engine_metrics.get("compute_metrics", {})
    return len(compute.get("jobs_by_pod", {}))


def _network_metric(results: SimulationResults, key: str) -> float:
    net = results.engine_metrics.get("network_metrics", {})
    return float(net.get(key, 0.0))


def _scatter(
    x_values: list[float],
    y_values: list[float],
    xlabel: str,
    ylabel: str,
    title: str,
) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(x_values, y_values, marker="o", linestyle="-")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    return fig


def latency_vs_constellation_size(all_results: list[SimulationResults]) -> Figure:
    """Mean delivery latency vs satellite count across sweep results."""
    if not all_results:
        return empty_figure("No sweep results available")
    x = [float(_satellite_count(r)) for r in all_results]
    y = [_network_metric(r, "avg_latency_s") for r in all_results]
    return _scatter(
        x, y, "Constellation size (satellites)", "Avg latency (s)", "Latency vs constellation size"
    )


def throughput_vs_num_pods(all_results: list[SimulationResults]) -> Figure:
    """Total transmitted packets vs pod count across sweep results."""
    if not all_results:
        return empty_figure("No sweep results available")
    x = [float(_pod_count(r)) for r in all_results]
    y = [_network_metric(r, "transmitted") for r in all_results]
    return _scatter(x, y, "Number of pods", "Packets transmitted", "Throughput vs number of pods")


def drop_rate_vs_load(all_results: list[SimulationResults]) -> Figure:
    """Drop rate vs offered load (transmitted packets) across sweep results."""
    if not all_results:
        return empty_figure("No sweep results available")
    x = [_network_metric(r, "transmitted") for r in all_results]
    y = [_network_metric(r, "drop_rate") for r in all_results]
    return _scatter(x, y, "Offered load (packets transmitted)", "Drop rate", "Drop rate vs load")


def physics_impact_vs_scale(all_results: list[SimulationResults]) -> Figure:
    """Physics-caused packet drops vs constellation size.

    Only results carrying a `physics_metrics` collector entry are
    plotted; results from non-physics runs are excluded.
    """
    physics_results = [r for r in all_results if "physics_metrics" in r.engine_metrics]
    if not physics_results:
        return empty_figure("No physics results available")
    x = [float(_satellite_count(r)) for r in physics_results]
    y = [
        float(r.engine_metrics.get("physics_metrics", {}).get("physics_caused_drops", 0))
        for r in physics_results
    ]
    return _scatter(
        x, y, "Constellation size (satellites)", "Physics-caused drops", "Physics impact vs scale"
    )
