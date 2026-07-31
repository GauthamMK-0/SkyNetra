"""
Domain layer (L1) — NetworkX topology graph builder.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

import networkx as nx

from skynetra.foundation.types import NodeId, Vector3


def build_topology_graph(
    positions: Dict[NodeId, Vector3],
    quality_fn: Callable[[NodeId, NodeId, Vector3, Vector3], float],
    threshold: float = 0.0,
    known_links: Optional[List[Tuple[NodeId, NodeId]]] = None,
) -> nx.Graph:
    graph = nx.Graph()
    for nid, pos in positions.items():
        graph.add_node(nid, position=pos)

    nodes = list(positions.items())
    if known_links:
        for a, b in known_links:
            if a in positions and b in positions:
                q = quality_fn(a, b, positions[a], positions[b])
                if q >= threshold:
                    graph.add_edge(a, b, quality=q)

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a_id, a_pos = nodes[i]
            b_id, b_pos = nodes[j]
            if not graph.has_edge(a_id, b_id):
                q = quality_fn(a_id, b_id, a_pos, b_pos)
                if q >= threshold:
                    graph.add_edge(a_id, b_id, quality=q)

    return graph
