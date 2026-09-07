"""
basic_run.py — A complete SkyNetra simulation run file demonstrating end-to-end
config, execution, metrics, and visualization.
"""

from __future__ import annotations

from pathlib import Path

# 1. Import configuration helpers and the simulation engine
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.interface.reporting import save_all_plots
from skynetra.orchestration.engine import OrbitDCSimulation


def main() -> None:
    # -------------------------------------------------------------
    # Step 1: Define the Simulation Configuration (FullConfig)
    # -------------------------------------------------------------
    config = FullConfig(
        # General simulation parameters
        simulation={
            "duration_s": 120.0,       # Total simulation duration in simulated seconds
            "seed": 42,                # Random seed for reproducible traffic and physics
            "record_events": True,     # Record individual events in results.events
        },

        # Walker-Delta Satellite Constellation geometry
        constellation={
            "n_planes": 3,             # Number of orbital planes
            "sats_per_plane": 6,       # Satellites per plane (Total sats = 3 * 6 = 18)
            "altitude_km": 550.0,      # LEO altitude
            "inclination_deg": 53.0,   # Orbital inclination
        },

        # On-Orbit Compute Pods (Accelerators)
        pods={
            "n_pods": 2,               # Number of compute pods in the network
        },

        # Ground Stations (Earth-fixed terrestrial endpoints)
        ground_stations={
            "n_ground_stations": 1,    # Number of ground stations
            "gsl_elevation_min_deg": 10.0, # Minimum elevation angle for satellite visibility
        },

        # Network Link Bandwidths
        network={
            "isl_capacity_gbps": 100.0, # Inter-satellite optical links (100 Gbps)
            "gsl_capacity_gbps": 10.0,  # Ground-to-satellite access links (10 Gbps)
        },

        # Routing Algorithm ("shortest_path" or "backpressure")
        routing={
            "strategy": "backpressure", # Use load-adaptive backpressure routing
        },

        # Space Physics Models
        physics={
            "thermal": {"enabled": True},   # Solar flux, eclipse cooling & pod heat dissipation
            "radiation": {"enabled": True}, # Total Ionizing Dose & Single Event Latch-ups
            "power": {"enabled": True},     # Solar panel generation & battery discharge
        },

        # Application Traffic Workloads
        workload={
            "active": ["ai_training_sync", "inference_query"],
            "ai_training_sync": {
                "sync_interval_s": 15.0,
                "gradient_size_bytes": 10_000_000, # 10 MB gradient exchange
                "gradient_flops": 1e11,            # Compute required for sync
            },
            "inference_query": {
                "mean_interval_s": 2.0,            # Query every ~2 seconds
                "query_size_bytes": 500,
                "flops_required": 1e9,             # 1 GFLOP per inference task
            },
        },

        # Metrics Collectors to track
        metrics={
            "active": [
                "network_metrics",
                "compute_metrics",
                "physics_metrics",
                "topology_metrics",
            ]
        },
    )

    # -------------------------------------------------------------
    # Step 2: Convert to an Executable Specification (SimulationSpec)
    # -------------------------------------------------------------
    spec = config_to_simulation_spec(config)

    # -------------------------------------------------------------
    # Step 3: Instantiate and Run the Simulation
    # -------------------------------------------------------------
    print(f"Starting simulation: {spec.routing_strategy} ({spec.sim_duration_s}s)...")
    sim = OrbitDCSimulation.from_spec(spec)
    results = sim.run()

    # -------------------------------------------------------------
    # Step 4: Inspect Results
    # -------------------------------------------------------------
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
    print("                 SKYNETRA SIMULATION EXECUTION REPORT                 ")
    print("=" * 70)
    print("Scenario Configuration:")
    print(f"  * Simulation Horizon  : {results.duration:.1f} simulated seconds")
    print("  * Constellation Mesh  : Walker-Delta 3 planes x 6 satellites (18 total @ 550 km)")
    print("  * On-Orbit Compute    : 2 Dedicated Accelerators (pod-1, pod-2)")
    print("  * Terrestrial Segment : 1 Ground Station (gs-1, >= 10.0 deg elevation mask)")
    print("  * Routing Policy      : Load-Adaptive Backpressure Routing")
    print("  * Active Workloads    : AI Training Sync (All-Reduce) + Inference Queries")

    print("\n[Network Forwarding & Delivery]")
    print(f"  * Packets Injected/Transmitted : {transmitted} packets")
    print(f"  * Successfully Received/Relayed: {delivered} packets")
    print(f"  * Packets Dropped (Congestion) : {dropped} packets")
    print(f"  * Mean End-to-End Latency      : {avg_latency_ms:.2f} ms")
    print(f"  * Packet Loss Rate             : {loss_rate:.2f}%")
    print(f"  * Delivery Completion Rate     : {delivery_rate:.2f}%")

    print("\n[On-Orbit Compute Data Center Servicing]")
    print(f"  * Compute Tasks Finished       : {comp.get('compute_jobs_completed', 0)} jobs")
    comp_flops = comp.get('compute_flops_completed', 0.0)
    print(f"  * Total FLOPs Accrued          : {comp_flops:.2e} FLOPS")
    comp_lat_ms = comp.get('avg_compute_latency_s', 0.0) * 1000
    print(f"  * Mean Compute Service Time    : {comp_lat_ms:.2f} ms")
    jobs_by_pod = comp.get("jobs_by_pod", {})
    if jobs_by_pod:
        print("  * Per-Pod Task Distribution    :")
        for pod_id, count in sorted(jobs_by_pod.items()):
            pct = (count / max(1, delivered)) * 100
            print(f"      - {pod_id:<8} : {count:>3} jobs ({pct:>5.1f}%)")

    print("\n[Space Environment & Physics Models]")
    active_models = phys.get('active_models', ['Thermal', 'Radiation', 'Power'])
    print(f"  * Active Physics Models        : {active_models}")
    print(f"  * Mean Radiative Core Temp     : {phys.get('avg_temperature', 0.0):.1f} K")
    print(f"  * Thermal Throttle Incidents   : {phys.get('thermal_throttle_events', 0)}")
    print(f"  * Radiation Latchup Faults     : {phys.get('radiation_fault_events', 0)}")
    energy_j = phys.get('total_energy_consumed', 0.0)
    print(f"  * Total Energy Consumed        : {energy_j:.2f} Joules")

    print("\n[Constellation Topology & Mesh Evolution]")
    print(f"  * Constellation Vertices       : {top.get('final_node_count', 0)} nodes")
    print(f"  * Active Intersatellite Links  : {top.get('final_edge_count', 0)} links")
    print(f"  * Topology Recomputations      : {top.get('topology_updates', 0)} updates")

    # -------------------------------------------------------------
    # Step 5: Save Visual Plots (PNGs)
    # -------------------------------------------------------------
    output_dir = Path("results/my_first_sim_plots")
    save_all_plots(results, str(output_dir))
    print(f"\nVisualizations successfully generated and saved to: {output_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
