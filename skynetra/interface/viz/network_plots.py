"""
Interface layer (L4) — network performance plots.

Every function here is a PLAIN FUNCTION, not a class implementing an
interface. Layer 4 does not need a swappable-strategy abstraction for
plotting the way L2 needs one for routing/physics/workload: viz has no
runtime behavioral variation that must be chosen by config — a plot is
a deterministic projection of a `SimulationResults` object, and the
user-facing choice of *which* plots to produce is made by the reporting
helpers / CLI, not by a strategy selector.

All functions derive their series from the raw L3 events and collector
summaries inside `SimulationResults`; they return a matplotlib Figure
and never mutate the results.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from skynetra.interface.viz._common import empty_figure
from skynetra.orchestration.events import PacketDeliveredEvent, PacketTransmitEvent
from skynetra.orchestration.results import SimulationResults


def latency_cdf_plot(results: SimulationResults) -> Figure:
    """Empirical CDF of per-packet delivery latency."""
    latencies = sorted(
        ev.latency_s for ev in results.events if isinstance(ev, PacketDeliveredEvent)
    )
    if not latencies:
        return empty_figure("No packet delivery data available")
    n = len(latencies)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(latencies, [(i + 1) / n for i in range(n)], drawstyle="steps-post")
    ax.set_xlabel("Latency (s)")
    ax.set_ylabel("CDF")
    ax.set_title("Packet delivery latency CDF")
    ax.grid(True, alpha=0.3)
    return fig


def throughput_plot(results: SimulationResults) -> Figure:
    """Throughput (transmits/s) binned into 1 s windows."""
    times = [ev.time for ev in results.events if isinstance(ev, PacketTransmitEvent)]
    if not times:
        return empty_figure("No packet transmit data available")
    nbins = max(1, int(results.duration))
    counts = [0] * nbins
    for t in times:
        counts[min(int(t), nbins - 1)] += 1
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.step(range(nbins), counts, where="post")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Packets transmitted / s")
    ax.set_title("Network throughput over time")
    ax.grid(True, alpha=0.3)
    return fig


def link_utilization_heatmap(results: SimulationResults) -> Figure:
    """Directed link utilization as an N x N transmit-count heatmap."""
    counts: dict[tuple[str, str], int] = {}
    for ev in results.events:
        if isinstance(ev, PacketTransmitEvent) and ev.to_node is not None:
            link = (str(ev.node_id), str(ev.to_node))
            counts[link] = counts.get(link, 0) + 1
    if not counts:
        return empty_figure("No link utilization data available")
    nodes = sorted({node for pair in counts for node in pair})
    index = {node: i for i, node in enumerate(nodes)}
    matrix = [[0] * len(nodes) for _ in nodes]
    for (src, dst), count in counts.items():
        matrix[index[src]][index[dst]] = count
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(matrix, cmap="viridis")
    fig.colorbar(im, ax=ax, label="transmits")
    ax.set_xticks(range(len(nodes)))
    ax.set_yticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=90)
    ax.set_yticklabels(nodes)
    ax.set_title("Link utilization (directed transmit counts)")
    return fig
