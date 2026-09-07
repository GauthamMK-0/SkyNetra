"""
Interface layer (L4) — High-level user API for rapid simulation execution.

Provides the `simulate()` entry point to run Walker-Delta satellite constellation
Space Data Center (SDC) simulations with sensible defaults in 2-3 lines of code.

May import from: interface, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Literal

from skynetra.interface.config.defaults import config_to_simulation_spec
from skynetra.interface.config.schema import (
    ConstellationConfigModel,
    FullConfig,
    GroundStationConfig,
    MetricsConfig,
    NetworkConfig,
    PhysicsConfig,
    PodConfig,
    RoutingConfig,
    SimulationConfig,
    WorkloadConfig,
)
from skynetra.interface.reporting import save_all_plots
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.results import SimulationResults


def simulate(
    duration_s: float = 60.0,
    constellation: tuple[int, int] | str = (3, 6),
    pods: int = 2,
    ground_stations: int = 1,
    routing: Literal["shortest_path", "backpressure"] = "backpressure",
    workload: str | list[str] = "inference",
    physics: bool = True,
    seed: int = 42,
    config: FullConfig | dict[str, Any] | None = None,
    **kwargs: Any,
) -> SimulationResults:
    """Run an end-to-end SkyNetra simulation with concise, intuitive arguments.

    Parameters
    ----------
    duration_s:
        Total simulated duration in seconds (default: 60.0s).
    constellation:
        Constellation geometry: either a tuple `(n_planes, sats_per_plane)` or
        a string like `"3x6"` (default: 3 planes x 6 sats = 18 satellites).
    pods:
        Number of on-orbit compute pods (default: 2).
    ground_stations:
        Number of Earth-fixed ground stations (default: 1).
    routing:
        Routing policy: "backpressure" or "shortest_path" (default: "backpressure").
    workload:
        Application traffic: "inference", "training" (or "ai_training"),
        "federated", or a list of workload names (default: "inference").
    physics:
        Whether to enable space physics models (thermal, radiation, power).
    seed:
        Random seed for reproducible traffic and physics faults (default: 42).
    config:
        Optional complete `FullConfig` or dictionary overlay. If provided,
        takes precedence over the individual parameters.
    **kwargs:
        Additional custom parameters forwarded to the underlying config schema.

    Returns
    -------
    SimulationResults
        Results object with typed accessors (.network, .compute, .physics, .topology),
        terminal reporting (.report()), and chart generation (.plot()).
    """
    # Ensure reporting plotter is registered in SimulationResults
    _ = save_all_plots

    if config is not None:
        if isinstance(config, FullConfig):
            cfg = config
        else:
            cfg = FullConfig.model_validate(config)
        spec = config_to_simulation_spec(cfg)
        return OrbitDCSimulation.from_spec(spec).run()

    # Parse constellation geometry
    if isinstance(constellation, str):
        parts = constellation.lower().split("x")
        n_planes = int(parts[0].strip())
        sats_per_plane = int(parts[1].strip())
    else:
        n_planes, sats_per_plane = constellation

    # Parse active workloads
    workload_names: list[str] = []
    wl_items = [workload] if isinstance(workload, str) else list(workload)
    for w in wl_items:
        w_lower = w.lower()
        if "infer" in w_lower:
            workload_names.append("inference_query")
        elif "train" in w_lower or "all_reduce" in w_lower:
            workload_names.append("ai_training_sync")
        elif "fed" in w_lower:
            workload_names.append("federated_learning")
        else:
            workload_names.append(w)

    workload_cfg: dict[str, Any] = {
        "active": workload_names,
        "inference_query": {
            "mean_interval_s": kwargs.get("inference_interval_s", 2.5),
            "query_size_bytes": 1024,
            "flops_required": 1e9,
        },
        "ai_training_sync": {
            "sync_interval_s": kwargs.get(
                "sync_interval_s", min(10.0, max(2.0, duration_s / 3.0))
            ),
            "gradient_size_bytes": 10_000_000,
            "gradient_flops": 1e11,
        },
        "federated_learning": {
            "n_rounds": kwargs.get("fl_rounds", 5),
            "round_interval_s": kwargs.get("fl_interval_s", 50.0),
            "worker_model_size_bytes": 1_000_000,
            "broadcast_size_bytes": 1_000_000,
            "aggregate_flops": 5e10,
        },
    }

    full_cfg = FullConfig(
        simulation=SimulationConfig(
            duration_s=duration_s,
            seed=seed,
            record_events=True,
        ),
        constellation=ConstellationConfigModel(
            n_planes=n_planes,
            sats_per_plane=sats_per_plane,
            altitude_km=kwargs.get("altitude_km", 550.0),
            inclination_deg=kwargs.get("inclination_deg", 53.0),
        ),
        pods=PodConfig(
            n_pods=pods,
        ),
        ground_stations=GroundStationConfig(
            n_ground_stations=ground_stations,
            gsl_elevation_min_deg=kwargs.get("gsl_elevation_min_deg", 10.0),
        ),
        network=NetworkConfig(
            isl_capacity_gbps=kwargs.get("isl_capacity_gbps", 100.0),
            gsl_capacity_gbps=kwargs.get("gsl_capacity_gbps", 10.0),
        ),
        routing=RoutingConfig(
            strategy=routing,
        ),
        physics=PhysicsConfig(
            thermal={"enabled": physics},
            radiation={"enabled": physics},
            power={"enabled": physics},
        ),
        workload=WorkloadConfig(
            active=workload_names,
            inference_query=workload_cfg["inference_query"],
            ai_training_sync=workload_cfg["ai_training_sync"],
            federated_learning=workload_cfg["federated_learning"],
        ),
        metrics=MetricsConfig(
            active=[
                "network_metrics",
                "compute_metrics",
                "physics_metrics",
                "topology_metrics",
            ]
        ),
    )

    spec = config_to_simulation_spec(full_cfg)
    return OrbitDCSimulation.from_spec(spec).run()
