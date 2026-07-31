"""
Interface layer (L4) — ISL connectivity visualization.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import networkx as nx


def plot_isl_connectivity(
    graph: nx.Graph,
    title: str = "ISL Connectivity",
    ax: Any = None,
) -> Any:
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    else:
        fig = ax.figure
    pos = nx.get_node_attributes(graph, "position")
    pos_2d = {n: (p[0], p[1]) for n, p in pos.items()} if pos else nx.spring_layout(graph, seed=42)
    nx.draw_networkx_nodes(graph, pos=pos_2d, ax=ax, node_size=50, node_color="blue")
    nx.draw_networkx_edges(
        graph, pos=pos_2d, ax=ax, alpha=0.5,
        width=[d["quality"] * 2 for _, _, d in graph.edges(data=True)],
    )
    ax.set_title(title)
    ax.set_aspect("equal")
    return fig
