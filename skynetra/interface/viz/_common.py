"""
Interface layer (L4) — shared visualization helpers.

Internal module; the public plotting API lives in the sibling modules
`network_plots`, `scaling_plots`, `topology_viz`, and `physics_plots`.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from skynetra.orchestration.results import SimulationResults


def empty_figure(message: str) -> Figure:
    """A figure containing only a centered message (empty-data fallback)."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.axis("off")
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=12,
        transform=ax.transAxes,
    )
    return fig


def has_collector(results: SimulationResults, name: str) -> bool:
    return name in results.engine_metrics
