"""
Engines layer (L2) — radiation physics model.

TID/SEU-style dose accumulation. The dose rate is the background rate,
optionally boosted inside the South-Atlantic-Anomaly phase window and
again inside periodic solar-event windows (both deterministic, no
hidden randomness). Cumulative dose drives two Layer 1 effects:

  * latch-up: at `latchup_threshold_rad` the model reports
    `fault_probability = 1.0`, which `Node.update_physics` turns into
    `_fault_active` (threshold 0.5) — the node goes non-operational.
  * degradation: Layer 1's `radiation_degradation_factor()` halves
    effective compute at `RADIATION_REFERENCE_DOSE_RAD` (1000 rad).

Links carry a `radiation_bit_error_rate` proportional to the current
background dose rate.

Disabled models return the node's current physics state unchanged.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.foundation.math_utils import kepler_period_s
from skynetra.foundation.time_utils import sim_time_to_orbital_phase
from skynetra.foundation.types import NodeId, Vector3

BACKGROUND_DOSE_RATE_RAD_S = 0.01
SAA_BOOST_FACTOR = 10.0
SAA_PHASE_START_F = 0.5
SAA_PHASE_WIDTH_F = 0.1
SOLAR_EVENT_PERIOD_S = 604800.0
SOLAR_EVENT_DURATION_S = 3600.0
SOLAR_EVENT_PHASE_SHIFT_F = 0.5
SOLAR_EVENT_DOSE_MULTIPLIER = 100.0
LATCHUP_THRESHOLD_RAD = 1000.0
BER_SCALE = 1e-3


class RadiationModel(PhysicsModel):
    """TID accumulation with SAA and solar-event windows and latch-up."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._background_dose_rate_rad_s = float(
            self._config.get("background_dose_rate_rad_s", BACKGROUND_DOSE_RATE_RAD_S)
        )
        self._saa_boost_factor = float(
            self._config.get("saa_boost_factor", SAA_BOOST_FACTOR)
        )
        self._saa_phase_start_f = float(
            self._config.get("saa_phase_start_f", SAA_PHASE_START_F)
        )
        self._saa_phase_width_f = float(
            self._config.get("saa_phase_width_f", SAA_PHASE_WIDTH_F)
        )
        self._solar_event_period_s = float(
            self._config.get("solar_event_period_s", SOLAR_EVENT_PERIOD_S)
        )
        self._solar_event_duration_s = float(
            self._config.get("solar_event_duration_s", SOLAR_EVENT_DURATION_S)
        )
        self._solar_event_phase_shift_f = float(
            self._config.get(
                "solar_event_phase_shift_f", SOLAR_EVENT_PHASE_SHIFT_F
            )
        )
        self._solar_event_dose_multiplier = float(
            self._config.get(
                "solar_event_dose_multiplier", SOLAR_EVENT_DOSE_MULTIPLIER
            )
        )
        self._latchup_threshold_rad = float(
            self._config.get("latchup_threshold_rad", LATCHUP_THRESHOLD_RAD)
        )
        self._ber_scale = float(self._config.get("ber_scale", BER_SCALE))

    def dose_rate_rad_s(self, time_s: float, constellation: ConstellationConfig) -> float:
        """Total deterministic dose rate at `time_s` (background + boosts)."""
        rate = self._background_dose_rate_rad_s
        period_s = kepler_period_s(constellation.altitude_km)
        phase = sim_time_to_orbital_phase(time_s, period_s)
        if self._saa_phase_start_f <= phase < self._saa_phase_start_f + self._saa_phase_width_f:
            rate *= self._saa_boost_factor
        event_phase = (
            (time_s + self._solar_event_phase_shift_f * self._solar_event_period_s)
            % self._solar_event_period_s
        ) / self._solar_event_period_s
        if event_phase < self._solar_event_duration_s / self._solar_event_period_s:
            rate *= self._solar_event_dose_multiplier
        return rate

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
        dose = float(node.physics_state["radiation_dose_rad"])
        dose += self.dose_rate_rad_s(time_s, constellation) * dt_s
        update: dict[str, Any] = {"radiation_dose_rad": dose}
        if dose >= self._latchup_threshold_rad:
            update["fault_probability"] = 1.0
        return update

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
        rate = self._background_dose_rate_rad_s
        ber = min(1.0, rate * self._ber_scale)
        return {"radiation_bit_error_rate": ber}

    def get_summary(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "background_dose_rate_rad_s": self._background_dose_rate_rad_s,
            "saa_boost_factor": self._saa_boost_factor,
            "solar_event_dose_multiplier": self._solar_event_dose_multiplier,
            "solar_event_phase_shift_f": self._solar_event_phase_shift_f,
            "latchup_threshold_rad": self._latchup_threshold_rad,
        }
