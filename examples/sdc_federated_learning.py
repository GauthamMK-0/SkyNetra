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

    transmitted = net.get("transmitted", 0)
    delivered = net.get("delivered", 0)
    dropped = net.get("dropped", 0)
    avg_latency_ms = net.get("avg_latency_s", 0.0) * 1000
    loss_rate = (dropped / max(1, transmitted)) * 100
    delivery_rate = (delivered / max(1, delivered + dropped)) * 100

    print("\n" + "=" * 70)
    print("            SDC FEDERATED LEARNING SIMULATION RESULTS                 ")
    print("=" * 70)
    print(f"Simulation Horizon : {results.duration:.1f} simulated seconds")
    print("Constellation Mesh : Walker-Delta 3 planes x 6 satellites (18 total)")
    print("Federated Clusters : 3 On-Orbit Compute Pods (Worker & Aggregator roles)")
    print("Ground Stations    : 2 Earth-Fixed Stations (gs-1, gs-2)")
    print("Training Protocol  : 3-Phase Synchronous FL (Gather -> Aggregate -> Broadcast)")
    print("Workload Profile   : 5 Rounds @ 50.0s interval | 1.0 MB model weights")

    print("\n[Federated Synchronization Network Metrics]")
    print(f"  * Total Gradient/Model Packets : {transmitted}")
    print(f"  * Successfully Received Models : {delivered}")
    print(f"  * Dropped/Lost Parameter Packets: {dropped}")
    print(f"  * Transmission Packet Loss Rate: {loss_rate:.2f}%")
    print(f"  * Delivery Completion Rate     : {delivery_rate:.2f}%")
    print(f"  * Mean Sync Transfer Latency   : {avg_latency_ms:.2f} ms")

    print("\n[On-Orbit Model Fusion & Aggregation Compute]")
    print(f"  * Aggregation Steps Finished   : {comp.get('compute_jobs_completed', 0)} jobs")
    comp_flops = comp.get('compute_flops_completed', 0.0)
    print(f"  * Model Parameter FLOPs Fused  : {comp_flops:.2e} FLOPS")
    comp_lat_ms = comp.get('avg_compute_latency_s', 0.0) * 1000
    print(f"  * Mean Parameter Fusion Time   : {comp_lat_ms:.2f} ms")
    print("  * Aggregation Pod Distribution :")
    jobs_by_pod = comp.get("jobs_by_pod", {})
    if jobs_by_pod:
        for pod_id, count in sorted(jobs_by_pod.items()):
            pct = (count / max(1, delivered)) * 100
            print(f"      - {pod_id:<8} : {count:>3} model merges ({pct:>5.1f}%)")

    print("\n[Space Environment Dynamics]")
    print(f"  * Mean SDC Thermal State       : {phys.get('avg_temperature', 0.0):.1f} K")
    print(f"  * Thermal Throttle Occurrences : {phys.get('thermal_throttle_events', 0)} events")
    print(f"  * Radiation Latchup Faults     : {phys.get('radiation_fault_events', 0)} events")

    print("\n[Constellation Topology & Mesh Evolution]")
    print(f"  * Constellation Vertices       : {top.get('final_node_count', 0)} nodes")
    print(f"  * Active Intersatellite Links  : {top.get('final_edge_count', 0)} links")
    print(f"  * Dynamic Route Recomputations : {top.get('topology_updates', 0)} ticks")

    plot_dir = Path("results/sdc_federated_learning_plots")
    save_all_plots(results, str(plot_dir))
    print(f"\nVisualizations successfully generated and saved to: {plot_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
