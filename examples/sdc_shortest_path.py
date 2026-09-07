"""
SDC scenario with shortest-path routing, full physics, and mixed
workloads — expressed end to end as a Layer 4 `FullConfig`.

Run:  python examples/sdc_shortest_path.py
"""

from __future__ import annotations

from pathlib import Path

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.interface.reporting import save_all_plots
from skynetra.orchestration.engine import OrbitDCSimulation


def main() -> None:
    config = FullConfig(
        simulation={"duration_s": 120.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6, "altitude_km": 550.0},
        pods={"n_pods": 4},
        ground_stations={"n_ground_stations": 1, "gsl_elevation_min_deg": 10.0},
        network={"isl_capacity_gbps": 100.0, "gsl_capacity_gbps": 10.0},
        routing={"strategy": "shortest_path"},
        physics={
            "thermal": {"enabled": True},
            "radiation": {"enabled": True},
            "power": {"enabled": True},
        },
        workload={
            "active": ["ai_training_sync", "inference_query"],
            "ai_training_sync": {
                "pattern": "all_reduce",
                "sync_interval_s": 15.0,
                "gradient_size_bytes": 10_000_000,
                "gradient_flops": 1e11,
            },
            "inference_query": {
                "mean_interval_s": 3.0,
                "query_size_bytes": 1024,
                "flops_required": 1e9,
            },
        },
        metrics={
            "active": [
                "network_metrics",
                "compute_metrics",
                "topology_metrics",
                "physics_metrics",
            ]
        },
    )

    print("Running SDC Shortest-Path Simulation (120.0s)...")
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    net = results.engine_metrics.get("network_metrics", {})
    comp = results.engine_metrics.get("compute_metrics", {})
    phys = results.engine_metrics.get("physics_metrics", {})
    top = results.engine_metrics.get("topology_metrics", {})

    print("\n================ SDC SHORTEST-PATH RESULTS ================")
    print(f"Simulation Duration : {results.duration:.1f}s")
    print(
        f"Network Performance : transmitted={net.get('transmitted', 0)} | "
        f"delivered={net.get('delivered', 0)} | "
        f"dropped={net.get('dropped', 0)} | "
        f"avg_latency={net.get('avg_latency_s', 0.0) * 1000:.2f} ms | "
        f"drop_rate={net.get('drop_rate', 0.0) * 100:.2f}%"
    )
    print(
        f"Compute Performance : jobs_completed={comp.get('compute_jobs_completed', 0)} | "
        f"total_flops={comp.get('compute_flops_completed', 0.0):.2e} FLOPS | "
        f"avg_service_time={comp.get('avg_compute_latency_s', 0.0) * 1000:.2f} ms | "
        f"jobs_by_pod={comp.get('jobs_by_pod', {})}"
    )
    print(
        f"Space Physics State : avg_temp={phys.get('avg_temperature', 0.0):.1f} K | "
        f"throttling_events={phys.get('thermal_throttle_events', 0)} | "
        f"radiation_faults={phys.get('radiation_fault_events', 0)} | "
        f"active_models={phys.get('active_models', [])}"
    )
    print(
        f"Constellation Graph : nodes={top.get('final_node_count', 0)} | "
        f"edges={top.get('final_edge_count', 0)} | "
        f"topology_updates={top.get('topology_updates', 0)}"
    )

    plot_dir = Path("results/sdc_shortest_path_plots")
    save_all_plots(results, str(plot_dir))
    print(f"\nVisualizations saved to: {plot_dir}/")


if __name__ == "__main__":
    main()
