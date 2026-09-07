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

    transmitted = net.get("transmitted", 0)
    delivered = net.get("delivered", 0)
    dropped = net.get("dropped", 0)
    avg_latency_ms = net.get("avg_latency_s", 0.0) * 1000
    loss_rate = net.get("drop_rate", 0.0) * 100
    delivery_rate = (delivered / max(1, delivered + dropped)) * 100

    print("\n" + "=" * 70)
    print("               SDC SHORTEST-PATH SIMULATION RESULTS                   ")
    print("=" * 70)
    print(f"Simulation Horizon : {results.duration:.1f} simulated seconds")
    print("Constellation Mesh : Walker-Delta 3 planes x 6 satellites (18 total)")
    print("Computing Nodes    : 4 On-Orbit Pods (pods 1-4)")
    print("Routing Strategy   : Dijkstra Shortest Path (Physical Propagation Delay)")
    print("Active Workloads   : AI Training Sync (All-Reduce) + Inference Queries")

    print("\n[Space Network Performance]")
    print(f"  * Total Packets Injected/Transmitted : {transmitted}")
    print(f"  * Total Packets Successfully Relayed : {delivered}")
    print(f"  * Total Dropped Packets              : {dropped}")
    print(f"  * Network Packet Loss Rate           : {loss_rate:.2f}%")
    print(f"  * End-to-End Delivery Success Rate   : {delivery_rate:.2f}%")
    print(f"  * Average End-to-End Latency         : {avg_latency_ms:.2f} ms")

    print("\n[On-Orbit Space Data Center Compute Servicing]")
    print(f"  * Total Compute Tasks Completed      : {comp.get('compute_jobs_completed', 0)} jobs")
    comp_flops = comp.get('compute_flops_completed', 0.0)
    print(f"  * Aggregate FLOPs Accrued Across SDC : {comp_flops:.2e} FLOPS")
    comp_lat_ms = comp.get('avg_compute_latency_s', 0.0) * 1000
    print(f"  * Mean Compute Task Service Time     : {comp_lat_ms:.2f} ms")
    print("  * Pod Workload Distribution          :")
    jobs_by_pod = comp.get("jobs_by_pod", {})
    if jobs_by_pod:
        for pod_id, count in sorted(jobs_by_pod.items()):
            pct = (count / max(1, delivered)) * 100
            print(f"      - {pod_id:<8} : {count:>3} jobs ({pct:>5.1f}%)")

    print("\n[Space Environment & Physics Dynamics]")
    print(f"  * Active Physics Models              : {phys.get('active_models', [])}")
    print(f"  * Mean Core Radiative Temperature    : {phys.get('avg_temperature', 0.0):.1f} K")
    print(f"  * Thermal Throttle Incidents         : {phys.get('thermal_throttle_events', 0)}")
    print(f"  * Single Event Latchup (SEL) Faults  : {phys.get('radiation_fault_events', 0)}")

    print("\n[Constellation Topology & Mesh Evolution]")
    print(f"  * Constellation Vertices (Nodes)     : {top.get('final_node_count', 0)} nodes")
    print(f"  * Active Intersatellite Links (ISLs) : {top.get('final_edge_count', 0)} links")
    print(f"  * Periodic Topology Recomputations   : {top.get('topology_updates', 0)} ticks")

    plot_dir = Path("results/sdc_shortest_path_plots")
    save_all_plots(results, str(plot_dir))
    print(f"\nVisualizations successfully generated and saved to: {plot_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
