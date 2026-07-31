"""
Interface layer (L4) — scaling plots.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Any, Dict, List

import matplotlib.pyplot as plt


def plot_scaling_results(
    configs: List[str],
    metrics: Dict[str, List[float]],
    title: str = "Scaling Results",
    ax: Any = None,
) -> Any:
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 5))
    else:
        fig = ax.figure
    x = list(range(len(configs)))
    for label, values in metrics.items():
        ax.plot(x, values, marker="o", label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(configs, rotation=45, ha="right")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return fig
