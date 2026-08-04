"""
Engines layer (L2) — physics model abstract interface.

Layer 2 interface for physical-effect models. Each model computes
node/link state deltas and optional routing weight overrides.

PhysicsModel does NOT subclass any Layer 3 hook interface — Layer 3
orchestration wires physics ticks into the SimPy loop and calls these
methods directly; the coupling is one-directional (L3 depends on L2,
never the reverse).

Models are opt-in: `enabled` defaults to False and is read from the
config dict. Disabled models are filtered out by PhysicsOrchestrator
and, when called directly, return node state unchanged.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.foundation.types import LinkId, NodeId, Vector3


class PhysicsModel(ABC):
    """Layer 2 interface for physical-effect models.

    Each model computes per-node and per-link state deltas as plain
    dicts (Layer 3 applies them via `Node.update_physics` and the edge
    attribute schema) plus optional `weight_overrides` fed to routing
    engines.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self.enabled = self._config.get("enabled", False)

    @abstractmethod
    def compute_node_physics(
        self,
        node_id: NodeId,
        node: Node,
        sat_position: Vector3 | None,
        time_s: float,
        dt_s: float,
        constellation: ConstellationConfig,
    ) -> dict[str, Any]:
        """Return a physics-state delta dict for `node` (keys merged by
        Layer 3 via `Node.update_physics`). Disabled models return the
        node's current state unchanged.
        """
        ...

    @abstractmethod
    def compute_link_physics(
        self,
        node_a: NodeId,
        node_b: NodeId,
        distance_km: float,
        time_s: float,
        dt_s: float,
    ) -> dict[str, Any]:
        """Return an edge-attribute delta dict for the A->B link (keys
        merged into the Layer 1 edge schema).
        """
        ...

    def get_routing_weight_overrides(
        self,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        time_s: float,
    ) -> dict[LinkId, float]:
        """Per-link weight overrides fed to routing engines, or {}."""
        return {}

    def get_summary(self) -> dict[str, Any]:
        """Plain dict describing model configuration/state for Layer 3."""
        return {}
