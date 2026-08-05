"""Integration: full 300s simulation with thermal + radiation enabled."""

from __future__ import annotations

from skynetra.interface.config.defaults import (
    config_to_simulation_spec,
    get_physics_enabled_config,
)
from skynetra.interface.config.schema import FullConfig
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import PhysicsTickEvent


def _physics_config() -> FullConfig:
    cfg = get_physics_enabled_config()
    cfg.simulation.duration_s = 300.0
    cfg.physics.doppler["enabled"] = False
    if "physics_metrics" not in cfg.metrics.active:
        cfg.metrics.active.append("physics_metrics")
    return cfg


def test_full_sim_physics() -> None:
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(_physics_config())).run()

    assert "physics_metrics" in results.engine_metrics
    physics = results.engine_metrics["physics_metrics"]

    active = set(physics["active_models"])
    assert "ThermalModel" in active
    assert "RadiationModel" in active

    # mean constellation temperature is tracked and physical
    assert physics["avg_temperature"] is not None
    assert physics["avg_temperature"] > 0

    # radiation dose accumulates over the run
    ticks = [ev for ev in results.events if isinstance(ev, PhysicsTickEvent)]
    assert ticks, "physics tick loop did not publish any ticks"
    max_dose = max(
        ns["physics_state"]["radiation_dose_rad"] for ev in ticks for ns in ev.node_state.values()
    )
    assert max_dose > 0
