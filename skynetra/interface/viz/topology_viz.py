"""
Interface layer (L4) — orbit and ISL topology visualization.

`plot_orbit_and_isl` is a PLAIN FUNCTION over an explicit snapshot
dict, consistent with the other viz modules: no strategy interface is
needed because there is no config-selectable behavioral variation in
plotting — the function is a fixed projection of a snapshot.

Snapshot schema (documented contract for callers, e.g. a CLI or
notebook that captures `context` state mid-run):

    {
        "positions": {node_id: (x, y, z)},  # ECI km, z optional
        "edges": [(node_a, node_b), ...],   # ISL links
        "title": str,                       # optional, defaulted
    }

The plot is a 2D (x, y) projection with an equal aspect ratio.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from skynetra.interface.viz._common import empty_figure


def plot_orbit_and_isl(context_snapshot: dict[str, Any]) -> Figure:
    """Plot satellite positions and ISL edges from a context snapshot."""
    positions: dict[str, Any] = context_snapshot.get("positions", {})
    edges: list[Any] = context_snapshot.get("edges", [])
    title: str = context_snapshot.get("title", "Orbit and ISL topology")

    if not positions:
        return empty_figure("No topology snapshot data available")

    xy = {
        str(nid): (float(pos[0]), float(pos[1])) for nid, pos in positions.items() if len(pos) >= 2
    }
    fig, ax = plt.subplots(figsize=(10, 8))
    for a, b in edges:
        if str(a) in xy and str(b) in xy:
            ax.plot(
                [xy[str(a)][0], xy[str(b)][0]],
                [xy[str(a)][1], xy[str(b)][1]],
                color="gray",
                alpha=0.6,
                linewidth=0.8,
            )
    xs = [p[0] for p in xy.values()]
    ys = [p[1] for p in xy.values()]
    ax.scatter(xs, ys, s=20, c="steelblue")
    ax.set_title(title)
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_aspect("equal")
    return fig
