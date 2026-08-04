"""
Engines layer (L2) — physics orchestrator.

Composes a list of PhysicsModel instances. Layer 3's engine.py owns the
SimPy process that calls `run_tick()`; this class contains no SimPy
imports itself, keeping Layer 2 free of orchestration concerns.

`run_tick` is a pure computation step: it returns a result dict that
Layer 3 applies to the live graph/node registry:

    {
        "node_updates": {node_id: {...}},   # merged into Node.update_physics
        "link_updates": {(u, v): {...}},    # merged into edge attributes
        "weight_overrides": {link_id: float},
        "summary": {model_name: {...}},
    }

Only `enabled` models contribute anything; with none enabled every
section of the result is empty.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.foundation.types import LinkId, NodeId, Vector3


class PhysicsOrchestrator:
    """Composes a list of PhysicsModel instances (enabled only)."""

    def __init__(self, models: list[PhysicsModel]) -> None:
        self.models = [m for m in models if m.enabled]

    def run_tick(
        self,
        time_s: float,
        dt_s: float,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        positions: dict[NodeId, Vector3],
        constellation: ConstellationConfig,
    ) -> dict[str, Any]:
        """Pure computation step (no yield/env) — returns a result dict.

        Layer 3 applies `node_updates`/`link_updates` to the live
        graph/node registry and stores `weight_overrides` on
        SimulationContext.
        """
        node_updates: dict[NodeId, dict[str, Any]] = {}
        link_updates: dict[tuple[NodeId, NodeId], dict[str, Any]] = {}
        weight_overrides: dict[LinkId, float] = {}
        summary: dict[str, dict[str, Any]] = {}

        for model in self.models:
            for node_id, node in node_registry.items():
                delta = model.compute_node_physics(
                    node_id,
                    node,
                    positions.get(node_id),
                    time_s,
                    dt_s,
                    constellation,
                )
                if delta:
                    node_updates.setdefault(node_id, {}).update(delta)
            for node_a, node_b in graph.edges():
                distance_km = self._edge_distance_km(
                    graph, positions, node_a, node_b
                )
                delta = model.compute_link_physics(
                    node_a, node_b, distance_km, time_s, dt_s
                )
                if delta:
                    link_updates.setdefault((node_a, node_b), {}).update(delta)
            weight_overrides.update(
                model.get_routing_weight_overrides(graph, node_registry, time_s)
            )
            summary[model.__class__.__name__] = model.get_summary()

        return {
            "node_updates": node_updates,
            "link_updates": link_updates,
            "weight_overrides": weight_overrides,
            "summary": summary,
        }

    @staticmethod
    def _edge_distance_km(
        graph: nx.DiGraph,
        positions: dict[NodeId, Vector3],
        node_a: NodeId,
        node_b: NodeId,
    ) -> float:
        pos_a = positions.get(node_a) or graph.nodes[node_a].get("position")
        pos_b = positions.get(node_b) or graph.nodes[node_b].get("position")
        if pos_a is None or pos_b is None:
            return 0.0
        return math.dist(pos_a, pos_b)
