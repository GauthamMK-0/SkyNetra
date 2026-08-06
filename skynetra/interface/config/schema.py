"""
Interface layer (L4) — FullConfig Pydantic v2 schema.

May import from: any layer below (L0-L3). This is the closed, explicit
configuration schema for OrbitDC: every strategy is a named field, not a
plugin list. New strategies require adding a `Literal` option here and a
registry entry in the appropriate layer2/layer3 `registry.py`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class SimulationConfig(BaseModel):
    duration_s: float = 60.0
    seed: int = 42
    topology_update_interval_s: float = 10.0
    physics_tick_interval_s: float = 1.0


class ConstellationConfigModel(BaseModel):
    n_planes: int = 3
    sats_per_plane: int = 6
    altitude_km: float = 550.0
    inclination_deg: float = 55.0
    phase_offset_f: int = 1
    raan_spread_deg: float = 360.0


class PodConfig(BaseModel):
    n_pods: int = 1


class GroundStationConfig(BaseModel):
    n_ground_stations: int = 1
    gsl_elevation_min_deg: float = 10.0


class NetworkConfig(BaseModel):
    isl_capacity_gbps: float = 100.0
    gsl_capacity_gbps: float = 10.0


class RoutingConfig(BaseModel):
    strategy: Literal["shortest_path", "backpressure"] = "shortest_path"
    config: dict[str, Any] = {}


class PhysicsConfig(BaseModel):
    thermal: dict[str, Any] = {
        "enabled": False,
        "throttle_temp_k": 340.0,
        "critical_temp_k": 380.0,
    }
    radiation: dict[str, Any] = {
        "enabled": False,
        "dose_rate_rad_s": 2.78e-5,
        "latch_up_dose_threshold_rad": 1e6,
    }
    power: dict[str, Any] = {
        "enabled": False,
        "solar_panel_w": 3000.0,
        "battery_capacity_wh": 500.0,
    }
    doppler: dict[str, Any] = {"enabled": False}


class WorkloadConfig(BaseModel):
    active: list[str] = ["ai_training_sync", "inference_query"]
    ai_training_sync: dict[str, Any] = {
        "sync_interval_s": 10.0,
        "sync_size_bytes": 500_000_000,
    }
    inference_query: dict[str, Any] = {"arrival_rate_rps": 10.0}
    federated_learning: dict[str, Any] = {}


class MetricsConfig(BaseModel):
    active: list[str] = ["network_metrics", "compute_metrics", "topology_metrics"]


class FullConfig(BaseModel):
    simulation: SimulationConfig = SimulationConfig()
    constellation: ConstellationConfigModel = ConstellationConfigModel()
    pods: PodConfig = PodConfig()
    ground_stations: GroundStationConfig = GroundStationConfig()
    network: NetworkConfig = NetworkConfig()
    routing: RoutingConfig = RoutingConfig()
    physics: PhysicsConfig = PhysicsConfig()
    workload: WorkloadConfig = WorkloadConfig()
    metrics: MetricsConfig = MetricsConfig()
    model_config = ConfigDict(extra="forbid")
    # NOTE: "forbid" not "allow" — layered config is a closed, explicit
    # schema by design; there is no open plugin list to extend at
    # runtime. New strategies require adding a Literal option and a
    # registry entry in the appropriate layer2/layer3 registry.py.
