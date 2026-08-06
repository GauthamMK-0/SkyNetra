"""
SDC scenario with shortest-path routing, full physics, and mixed
workloads — expressed end to end as a Layer 4 `FullConfig`.

Run:  python examples/sdc_shortest_path.py
"""

from __future__ import annotations

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation


def main() -> None:
    config = FullConfig(
        simulation={"duration_s": 120.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6},
        pods={"n_pods": 4},
        ground_stations={"n_ground_stations": 1, "gsl_elevation_min_deg": 10.0},
        network={"isl_capacity_gbps": 100.0, "gsl_capacity_gbps": 10.0},
        routing={"strategy": "shortest_path"},
        physics={"thermal": {"enabled": True}, "radiation": {"enabled": True}},
        workload={
            "active": ["ai_training_sync", "inference_query"],
            "ai_training_sync": {"sync_interval_s": 10.0, "sync_size_bytes": 500_000_000},
            "inference_query": {"arrival_rate_rps": 5.0},
        },
        metrics={"active": [
            "network_metrics", "compute_metrics", "topology_metrics", "physics_metrics",
        ]},
    )

    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    print(f"SDC Shortest-Path simulation: {results.duration}s")
    for name, data in results.engine_metrics.items():
        print(f"  {name}: {data}")


if __name__ == "__main__":
    main()
