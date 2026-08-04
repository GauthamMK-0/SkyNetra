"""
Engines layer (L2) — thermal physics model.

Eclipse-cycling thermal model. In sunlight the node relaxes toward a
solar equilibrium temperature; inside the eclipse window (computed with
the Layer 0 `is_in_eclipse` helper and the constellation's orbital
period) it relaxes toward a cold eclipse equilibrium. The approach rate
is scaled by absorption `(1 - albedo)` in sunlight and by `emissivity`
in eclipse — both in [0, 1].

Higher temperatures throttle on-orbit compute: Layer 1's PodNode
`available_compute_flops()` applies `thermal_degradation_factor()`
(exp decay above TEMP_NOMINAL_K), and `temperature_k >= 400.0` drives
the node into a fault state via `Node.update_physics`.

Disabled models return the node's current physics state unchanged.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.foundation.math_utils import kepler_period_s
from skynetra.foundation.time_utils import is_in_eclipse
from skynetra.foundation.types import NodeId, Vector3

SOLAR_EQUILIBRIUM_K = 320.0
ECLIPSE_EQUILIBRIUM_K = 200.0
TIME_CONSTANT_S = 3600.0
ECLIPSE_FRACTION = 0.35


class ThermalModel(PhysicsModel):
    """Relaxation-based thermal model with eclipse cycling."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._albedo = float(self._config.get("albedo", 0.3))
        self._emissivity = float(self._config.get("emissivity", 0.8))
        self._solar_equilibrium_k = float(
            self._config.get("solar_equilibrium_k", SOLAR_EQUILIBRIUM_K)
        )
        self._eclipse_equilibrium_k = float(
            self._config.get("eclipse_equilibrium_k", ECLIPSE_EQUILIBRIUM_K)
        )
        self._time_constant_s = float(
            self._config.get("time_constant_s", TIME_CONSTANT_S)
        )
        self._eclipse_fraction = float(
            self._config.get("eclipse_fraction", ECLIPSE_FRACTION)
        )

    def compute_node_physics(
        self,
        node_id: NodeId,
        node: Node,
        sat_position: Vector3 | None,
        time_s: float,
        dt_s: float,
        constellation: ConstellationConfig,
    ) -> dict[str, Any]:
        if not self.enabled:
            return dict(node.physics_state)
        current = float(node.physics_state["temperature_k"])
        period_s = kepler_period_s(constellation.altitude_km)
        in_eclipse = is_in_eclipse(time_s, period_s, self._eclipse_fraction)
        if in_eclipse:
            target = self._eclipse_equilibrium_k
            rate = self._emissivity
        else:
            target = self._solar_equilibrium_k
            rate = 1.0 - self._albedo
        delta = (target - current) * (dt_s / self._time_constant_s) * rate
        return {"temperature_k": current + delta}

    def compute_link_physics(
        self,
        node_a: NodeId,
        node_b: NodeId,
        distance_km: float,
        time_s: float,
        dt_s: float,
    ) -> dict[str, Any]:
        return {}

    def get_summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "albedo": self._albedo,
            "emissivity": self._emissivity,
            "solar_equilibrium_k": self._solar_equilibrium_k,
            "eclipse_equilibrium_k": self._eclipse_equilibrium_k,
            "time_constant_s": self._time_constant_s,
            "eclipse_fraction": self._eclipse_fraction,
        }
