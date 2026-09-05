"""
Interface layer (L4) — config load/save, presets, and the L4 -> L3
translation function.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.interface.config.schema import (
    ConstellationConfigModel,
    FullConfig,
    PodConfig,
    SimulationConfig,
)
from skynetra.orchestration.engine import OrbitDCSimulation


def load_config(path: str) -> FullConfig:
    p = Path(path)
    raw: dict[str, Any]
    if p.suffix in (".yaml", ".yml"):
        with open(p) as f:
            raw = yaml.safe_load(f) or {}
    elif p.suffix == ".json":
        with open(p) as f:
            raw = json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {p.suffix}")
    return FullConfig(**raw)


def save_config(config: FullConfig, path: str) -> None:
    p = Path(path)
    raw = config.model_dump(mode="json")
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix in (".yaml", ".yml"):
        with open(p, "w") as f:
            yaml.dump(raw, f, default_flow_style=False)
    elif p.suffix == ".json":
        with open(p, "w") as f:
            json.dump(raw, f, indent=2)
    else:
        raise ValueError(f"Unsupported config format: {p.suffix}")


def get_physics_enabled_config() -> FullConfig:
    cfg = FullConfig()
    cfg.physics.thermal["enabled"] = True
    cfg.physics.radiation["enabled"] = True
    cfg.physics.power["enabled"] = True
    return cfg


def get_minimal_config() -> FullConfig:
    return FullConfig(
        simulation=SimulationConfig(duration_s=60.0, seed=42),
        constellation=ConstellationConfigModel(n_planes=2, sats_per_plane=3),
        pods=PodConfig(n_pods=1),
    )


def config_to_simulation_spec(
    config: FullConfig,
) -> OrbitDCSimulation.SimulationSpec:
    """THE key translation function: converts the closed Pydantic
    FullConfig (Layer 4) into the plain SimulationSpec dataclass that
    Layer 3's OrbitDCSimulation.from_spec() expects. This is the single
    place where Layer 4 reaches down into Layer 3's types."""
    physics_specs: list[dict[str, Any]] = []
    for name, section in (
        ("thermal", config.physics.thermal),
        ("radiation", config.physics.radiation),
        ("power", config.physics.power),
        ("doppler", config.physics.doppler),
    ):
        if section.get("enabled"):
            physics_specs.append({"name": name, "config": dict(section)})

    workload_specs: list[dict[str, Any]] = [
        {"name": name, "config": dict(getattr(config.workload, name))}
        for name in config.workload.active
    ]
    metrics_specs: list[dict[str, Any]] = [{"name": name} for name in config.metrics.active]

    return OrbitDCSimulation.SimulationSpec(
        constellation=ConstellationConfig(
            n_planes=config.constellation.n_planes,
            sats_per_plane=config.constellation.sats_per_plane,
            altitude_km=config.constellation.altitude_km,
            inclination_deg=config.constellation.inclination_deg,
            phase_offset_f=config.constellation.phase_offset_f,
            raan_spread_deg=config.constellation.raan_spread_deg,
        ),
        n_pods=config.pods.n_pods,
        n_ground_stations=config.ground_stations.n_ground_stations,
        routing_strategy=config.routing.strategy,
        routing_config=dict(config.routing.config),
        physics_specs=physics_specs,
        workload_specs=workload_specs,
        metrics_specs=metrics_specs,
        sim_duration_s=config.simulation.duration_s,
        topology_update_interval_s=config.simulation.topology_update_interval_s,
        physics_tick_interval_s=config.simulation.physics_tick_interval_s,
        isl_capacity_gbps=config.network.isl_capacity_gbps,
        gsl_capacity_gbps=config.network.gsl_capacity_gbps,
        gsl_elevation_min_deg=config.ground_stations.gsl_elevation_min_deg,
        seed=config.simulation.seed,
        record_events=config.simulation.record_events,
    )
