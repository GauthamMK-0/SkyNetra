"""
Engines layer (L2) — power physics model.

Eclipse-cycling power model. In sunlight the solar array generates
`flux * area * efficiency` watts and the battery charges from the
surplus; inside the eclipse window generation drops to zero and the
battery discharges to supply `power_available_w` up to
`discharge_power_w`. Battery charge is tracked per node across ticks
(deterministic, no randomness); the `battery_charge_wh` value is
reported into the node physics state via `update_physics`.

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

SOLAR_FLUX_W_M2 = 1361.0
SOLAR_PANEL_AREA_M2 = 10.0
SOLAR_EFFICIENCY = 0.3
BATTERY_CAPACITY_WH = 1000.0
BATTERY_CHARGE_WH = 500.0
CHARGE_EFFICIENCY = 0.9
DISCHARGE_EFFICIENCY = 0.9
DISCHARGE_POWER_W = 100.0
ECLIPSE_FRACTION = 0.35


class PowerModel(PhysicsModel):
    """Solar generation with battery charge/discharge across eclipses."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._solar_flux_w_m2 = float(
            self._config.get("solar_flux_w_m2", SOLAR_FLUX_W_M2)
        )
        self._solar_panel_area_m2 = float(
            self._config.get("solar_panel_area_m2", SOLAR_PANEL_AREA_M2)
        )
        self._solar_efficiency = float(
            self._config.get("solar_efficiency", SOLAR_EFFICIENCY)
        )
        self._battery_capacity_wh = float(
            self._config.get("battery_capacity_wh", BATTERY_CAPACITY_WH)
        )
        self._charge_efficiency = float(
            self._config.get("charge_efficiency", CHARGE_EFFICIENCY)
        )
        self._discharge_efficiency = float(
            self._config.get("discharge_efficiency", DISCHARGE_EFFICIENCY)
        )
        self._discharge_power_w = float(
            self._config.get("discharge_power_w", DISCHARGE_POWER_W)
        )
        self._eclipse_fraction = float(
            self._config.get("eclipse_fraction", ECLIPSE_FRACTION)
        )
        self._initial_charge_wh = float(
            self._config.get("battery_charge_wh", BATTERY_CHARGE_WH)
        )
        self._battery_charge_wh: dict[NodeId, float] = {}

    def _charge_for(self, node_id: NodeId) -> float:
        if node_id not in self._battery_charge_wh:
            self._battery_charge_wh[node_id] = self._initial_charge_wh
        return self._battery_charge_wh[node_id]

    def generated_power_w(self, in_eclipse: bool) -> float:
        if in_eclipse:
            return 0.0
        return self._solar_flux_w_m2 * self._solar_panel_area_m2 * self._solar_efficiency

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
        period_s = kepler_period_s(constellation.altitude_km)
        in_eclipse = is_in_eclipse(time_s, period_s, self._eclipse_fraction)
        charge = self._charge_for(node_id)
        if in_eclipse:
            max_draw = charge / max(dt_s, 1e-9)
            draw = min(self._discharge_power_w, max_draw)
            charge = max(0.0, charge - draw * dt_s / self._discharge_efficiency)
            power_available = draw
        else:
            generated = self.generated_power_w(in_eclipse=False)
            charge = min(
                self._battery_capacity_wh,
                charge + generated * dt_s * self._charge_efficiency,
            )
            power_available = generated
        self._battery_charge_wh[node_id] = charge
        return {"power_available_w": power_available, "battery_charge_wh": charge}

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
            "solar_panel_area_m2": self._solar_panel_area_m2,
            "solar_efficiency": self._solar_efficiency,
            "battery_capacity_wh": self._battery_capacity_wh,
            "eclipse_fraction": self._eclipse_fraction,
        }
