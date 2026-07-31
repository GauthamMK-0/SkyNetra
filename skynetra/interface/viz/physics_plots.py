"""
Interface layer (L4) — physics state plots.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt


def plot_physics_state(
    time_series: Dict[str, List[float]],
    title: str = "Physics State",
    ax: Any = None,
) -> Any:
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    else:
        fig = ax.figure
    for label, values in time_series.items():
        ax.plot(values, label=label)
    ax.set_title(title)
    ax.set_xlabel("Time step")
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig
