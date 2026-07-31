"""
Interface layer (L4) — network topology plots.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import networkx as nx


def plot_network_topology(
    graph: nx.Graph,
    title: str = "Network Topology",
    ax: Any = None,
    **kwargs: Any,
) -> Any:
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    else:
        fig = ax.figure
    pos = nx.spring_layout(graph, seed=42)
    nx.draw_networkx(
        graph,
        pos=pos,
        ax=ax,
        node_color="skyblue",
        edge_color="gray",
        with_labels=True,
        **kwargs,
    )
    ax.set_title(title)
    return fig
