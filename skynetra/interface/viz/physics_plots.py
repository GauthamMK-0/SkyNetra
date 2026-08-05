"""
Interface layer (L4) — physics state plots.

Every function here is a PLAIN FUNCTION, not a class implementing an
interface — same reasoning as the sibling viz modules: plotting has no
runtime behavioral variation that must be chosen by config, so no
swappable-strategy abstraction is warranted at Layer 4.

Series are derived from `PhysicsTickEvent` payloads in the results
(per-node `physics_state` keyed by `temperature_k`, `radiation_dose_rad`,
`battery_charge_wh`, `power_available_w`), averaged across nodes per
tick. All functions gracefully return a "No physics data available"
text figure when `results.engine_metrics` has no `physics_metrics`
entry (or when the event log carries no physics ticks).

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from skynetra.interface.viz._common import empty_figure, has_collector
from skynetra.orchestration.events import PhysicsTickEvent
from skynetra.orchestration.results import SimulationResults

NO_PHYSICS_MESSAGE = "No physics data available"


def _tick_series(results: SimulationResults, state_key: str) -> tuple[list[float], list[float]]:
    """Per-tick (time, mean-of-key-across-nodes) series from events."""
    times: list[float] = []
    means: list[float] = []
    for ev in results.events:
        if not isinstance(ev, PhysicsTickEvent):
            continue
        values = [
            float(node_state["physics_state"][state_key])
            for node_state in ev.node_state.values()
            if state_key in node_state["physics_state"]
        ]
        if values:
            times.append(ev.time)
            means.append(sum(values) / len(values))
    return times, means


def _physics_available(results: SimulationResults) -> bool:
    if not has_collector(results, "physics_metrics"):
        return False
    return any(isinstance(ev, PhysicsTickEvent) for ev in results.events)


def temperature_timeseries(results: SimulationResults) -> Figure:
    """Mean node temperature over time."""
    if not _physics_available(results):
        return empty_figure(NO_PHYSICS_MESSAGE)
    times, means = _tick_series(results, "temperature_k")
    if not times:
        return empty_figure(NO_PHYSICS_MESSAGE)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times, means, marker="o", markersize=3)
    ax.axhline(340.0, color="orange", linestyle="--", alpha=0.7, label="throttle threshold")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mean temperature (K)")
    ax.set_title("Node temperature over time")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


def radiation_dose_accumulation(results: SimulationResults) -> Figure:
    """Mean accumulated radiation dose over time."""
    if not _physics_available(results):
        return empty_figure(NO_PHYSICS_MESSAGE)
    times, means = _tick_series(results, "radiation_dose_rad")
    if not times:
        return empty_figure(NO_PHYSICS_MESSAGE)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times, means, marker="o", markersize=3)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mean radiation dose (rad)")
    ax.set_title("Radiation dose accumulation")
    ax.grid(True, alpha=0.3)
    return fig


def power_state_timeseries(results: SimulationResults) -> Figure:
    """Mean battery charge (left axis) and power available (right axis)."""
    if not _physics_available(results):
        return empty_figure(NO_PHYSICS_MESSAGE)
    times, battery = _tick_series(results, "battery_charge_wh")
    if not times:
        return empty_figure(NO_PHYSICS_MESSAGE)
    _times2, power = _tick_series(results, "power_available_w")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(times, battery, marker="o", markersize=3, label="battery charge (Wh)")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mean battery charge (Wh)")
    ax2 = ax.twinx()
    ax2.plot(times, power, color="tab:orange", linestyle="--", label="power available (W)")
    ax2.set_ylabel("Mean power available (W)")
    ax.set_title("Power state over time")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="best")
    ax.grid(True, alpha=0.3)
    return fig


def physics_vs_network_impact(results: SimulationResults) -> Figure:
    """Grouped bars: physics-caused drops vs network delivered/dropped."""
    if not _physics_available(results):
        return empty_figure(NO_PHYSICS_MESSAGE)
    physics = results.engine_metrics.get("physics_metrics", {})
    network = results.engine_metrics.get("network_metrics", {})
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ["physics_caused_drops", "network_delivered", "network_dropped"]
    values = [
        float(physics.get("physics_caused_drops", 0)),
        float(network.get("delivered", 0)),
        float(network.get("dropped", 0)),
    ]
    ax.bar(labels, values)
    ax.set_ylabel("Packets")
    ax.set_title("Physics vs network impact")
    ax.grid(True, alpha=0.3)
    return fig
