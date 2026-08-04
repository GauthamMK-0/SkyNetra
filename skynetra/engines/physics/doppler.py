"""
Engines layer (L2) — Doppler physics model.

Doppler shift from radial velocity. The model is stateful across ticks:
it stores the previous inter-node distance per directed link and
derives the radial velocity by finite difference over `dt_s`:

    v_radial = (d(t) - d(t - dt)) / dt
    doppler_shift_hz = carrier_freq_hz * v_radial / speed_of_light

The first tick (no previous sample) reports a shift of 0 Hz.
`get_routing_weight_overrides` reports the normalized |shift|/f_c per
link (from the most recent `compute_link_physics` pass), so an enabled
Doppler model can push routing away from fast-closing links.

Disabled models return no node deltas and no weight overrides.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.topology.isl import SPEED_OF_LIGHT_KM_S
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.foundation.types import LinkId, NodeId, Vector3

CARRIER_FREQ_HZ = 30e9
WEIGHT_COEFFICIENT = 1.0


class DopplerModel(PhysicsModel):
    """Doppler shift from finite-difference radial velocity."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._carrier_freq_hz = float(
            self._config.get("carrier_freq_hz", CARRIER_FREQ_HZ)
        )
        self._weight_coefficient = float(
            self._config.get("weight_coefficient", WEIGHT_COEFFICIENT)
        )
        self._prev_distance_km: dict[LinkId, float] = {}
        self._last_shift_hz: dict[LinkId, float] = {}

    def doppler_shift_hz(self, radial_velocity_kms: float) -> float:
        return self._carrier_freq_hz * radial_velocity_kms / SPEED_OF_LIGHT_KM_S

    def compute_node_physics(
        self,
        node_id: NodeId,
        node: Node,
        sat_position: Vector3 | None,
        time_s: float,
        dt_s: float,
        constellation: ConstellationConfig,
    ) -> dict[str, Any]:
        # Doppler is a link effect only; node physics state is untouched.
        if not self.enabled:
            return dict(node.physics_state)
        return {}

    def compute_link_physics(
        self,
        node_a: NodeId,
        node_b: NodeId,
        distance_km: float,
        time_s: float,
        dt_s: float,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {}
        link = LinkId(f"{node_a}->{node_b}")
        prev = self._prev_distance_km.get(link)
        self._prev_distance_km[link] = distance_km
        if prev is None:
            shift = 0.0
        else:
            radial_velocity_kms = (distance_km - prev) / max(dt_s, 1e-9)
            shift = self.doppler_shift_hz(radial_velocity_kms)
        self._last_shift_hz[link] = shift
        return {"doppler_shift_hz": shift}

    def get_routing_weight_overrides(
        self,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        time_s: float,
    ) -> dict[LinkId, float]:
        if not self.enabled:
            return {}
        overrides: dict[LinkId, float] = {}
        for node_a, node_b in graph.edges():
            link = LinkId(f"{node_a}->{node_b}")
            shift = self._last_shift_hz.get(link, 0.0)
            overrides[link] = self._weight_coefficient * abs(shift) / self._carrier_freq_hz
        return overrides

    def get_summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "carrier_freq_hz": self._carrier_freq_hz,
            "weight_coefficient": self._weight_coefficient,
        }
