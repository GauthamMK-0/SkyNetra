"""
Worked example: extending the physics layer WITHOUT modifying
`skynetra/engines/physics/registry.py`.

Simplified debris conjunction model: on each tick, every ISL has a
small per-second probability of a debris encounter that "disrupts" the
link for a maneuver duration. Disruption is expressed through
`get_routing_weight_overrides()` — a near-infinite penalty on affected
links (both directions) — exactly how the L2 physics interface lets a
model influence routing without touching the routing layer.

Composed the recommended way — no registry mutation:

    from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
    sim = OrbitDCSimulation.from_layers(
        ...,
        physics_orchestrator=PhysicsOrchestrator([
            DebrisProximityModel({"enabled": True, "seed": 7}),
        ]),
        ...)

Config keys: `enabled`, `collision_probability` (per-second per-link
encounter rate, default 0.02), `maneuver_duration_s` (default 60.0),
`link_penalty` (default 1e6), `seed` (default 42). The RNG is seeded
from config, so runs are deterministic.
"""

from __future__ import annotations

import random
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.foundation.types import LinkId, NodeId, Vector3


class DebrisProximityModel(PhysicsModel):
    """Simplified debris conjunction model: random events disrupt ISLs
    for a maneuver duration, and `get_routing_weight_overrides()` adds a
    near-infinite penalty on affected links.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.collision_probability = float(self._config.get("collision_probability", 0.02))
        self.maneuver_duration_s = float(self._config.get("maneuver_duration_s", 60.0))
        self.link_penalty = float(self._config.get("link_penalty", 1e6))
        self._rng = random.Random(self._config.get("seed", 42))
        self._disrupted_until: dict[tuple[NodeId, NodeId], float] = {}

    def compute_node_physics(
        self,
        node_id: NodeId,
        node: Node,
        sat_position: Vector3 | None,
        time_s: float,
        dt_s: float,
        constellation: ConstellationConfig,
    ) -> dict[str, Any]:
        # Debris proximity affects links, not node state.
        return {}

    def compute_link_physics(
        self,
        node_a: NodeId,
        node_b: NodeId,
        distance_km: float,
        time_s: float,
        dt_s: float,
    ) -> dict[str, Any]:
        link = (node_a, node_b)
        if time_s < self._disrupted_until.get(link, 0.0):
            return {}
        if self._rng.random() < self.collision_probability * dt_s:
            self._disrupted_until[link] = time_s + self.maneuver_duration_s
        return {}

    def get_routing_weight_overrides(
        self,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        time_s: float,
    ) -> dict[LinkId, float]:
        overrides: dict[LinkId, float] = {}
        for (node_a, node_b), until in self._disrupted_until.items():
            if time_s < until and graph.has_edge(node_a, node_b):
                overrides[LinkId(f"{node_a}->{node_b}")] = self.link_penalty
                overrides[LinkId(f"{node_b}->{node_a}")] = self.link_penalty
        return overrides

    def get_summary(self) -> dict[str, Any]:
        return {
            "name": "debris_proximity",
            "disrupted_links": len(self._disrupted_until),
        }
