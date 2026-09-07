"""
Federated Learning in Space Data Centers (SDC):
Simulates 3-phase on-orbit FL:
  1. Worker nodes upload local model weights to the central aggregator pod (Gather)
  2. Aggregator pod fuses parameters (Compute service time governed by aggregate_flops)
  3. Aggregator broadcasts global weights back to all workers (Broadcast)

Run:  python examples/sdc_federated_learning.py
"""

from __future__ import annotations

from pathlib import Path

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.interface.reporting import save_all_plots
from skynetra.orchestration.engine import OrbitDCSimulation


def main() -> None:
    config = FullConfig(
        simulation={"duration_s": 300.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6, "altitude_km": 550.0},
        pods={"n_pods": 3},
        ground_stations={"n_ground_stations": 2, "gsl_elevation_min_deg": 10.0},
        network={"isl_capacity_gbps": 100.0, "gsl_capacity_gbps": 10.0},
        routing={"strategy": "backpressure"},
        physics={"thermal": {"enabled": True}, "radiation": {"enabled": True}},
        workload={
            "active": ["federated_learning"],
            "federated_learning": {
                "n_rounds": 5,
                "round_interval_s": 50.0,
                "worker_model_size_bytes": 1_000_000,
                "broadcast_size_bytes": 1_000_000,
                "aggregate_flops": 5e10,
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

    print("Running SDC Federated Learning Simulation (300.0s)...")
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    net = results.engine_metrics.get("network_metrics", {})
    comp = results.engine_metrics.get("compute_metrics", {})
    phys = results.engine_metrics.get("physics_metrics", {})
    top = results.engine_metrics.get("topology_metrics", {})

    print("\n================ SDC FEDERATED LEARNING RESULTS ================")
    print(f"Simulation Duration : {results.duration:.1f}s")
    print(
        f"Network Performance : transmitted={net.get('transmitted', 0)} | "
        f"delivered={net.get('delivered', 0)} | "
        f"dropped={net.get('dropped', 0)} | "
        f"avg_latency={net.get('avg_latency_s', 0.0) * 1000:.2f} ms"
    )
    print(
        f"Compute Performance : aggregation_jobs={comp.get('compute_jobs_completed', 0)} | "
        f"total_flops={comp.get('compute_flops_completed', 0.0):.2e} FLOPS | "
        f"jobs_by_pod={comp.get('jobs_by_pod', {})}"
    )
    print(
        f"Space Physics State : avg_temp={phys.get('avg_temperature', 0.0):.1f} K | "
        f"throttling_events={phys.get('thermal_throttle_events', 0)} | "
        f"radiation_faults={phys.get('radiation_fault_events', 0)}"
    )
    print(
        f"Constellation Graph : nodes={top.get('final_node_count', 0)} | "
        f"edges={top.get('final_edge_count', 0)} | "
        f"topology_updates={top.get('topology_updates', 0)}"
    )

    plot_dir = Path("results/sdc_federated_learning_plots")
    save_all_plots(results, str(plot_dir))
    print(f"\nVisualizations saved to: {plot_dir}/")


if __name__ == "__main__":
    main()
