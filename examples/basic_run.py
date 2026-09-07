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
    print("\n================ SIMULATION RESULTS ================")
    print(f"Wall-clock runtime completed for {results.duration:.1f} simulated seconds.")

    # 4a. Network Metrics
    net = results.engine_metrics.get("network_metrics", {})
    print("\n[Network Metrics]")
    print(f"  Packets Transmitted : {net.get('transmitted', 0)}")
    print(f"  Packets Delivered   : {net.get('delivered', 0)}")
    print(f"  Packets Dropped     : {net.get('dropped', 0)}")
    print(f"  Average Latency     : {net.get('avg_latency_s', 0.0) * 1000:.3f} ms")
    print(f"  Drop Rate           : {net.get('drop_rate', 0.0) * 100:.2f}%")

    # 4b. On-Orbit Compute Metrics
    comp = results.engine_metrics.get("compute_metrics", {})
    print("\n[Compute Metrics]")
    print(f"  Compute Tasks Finished : {comp.get('compute_jobs_completed', 0)}")
    print(f"  Total FLOPS Accrued    : {comp.get('total_flops_computed', 0.0):.2e} FLOPS")
    print(f"  Avg Compute Service Time: {comp.get('avg_compute_latency_s', 0.0) * 1000:.3f} ms")

    # 4c. Space Physics Metrics
    phys = results.engine_metrics.get("physics_metrics", {})
    print("\n[Physics Metrics]")
    print(f"  Thermal Throttling Events : {phys.get('thermal_throttling_events', 0)}")
    print(f"  Radiation Latchup Faults  : {phys.get('radiation_fault_events', 0)}")
    print(f"  Average Node Temperature  : {phys.get('avg_temperature_k', 0.0):.2f} K")

    # -------------------------------------------------------------
    # Step 5: Save Visual Plots (PNGs)
    # -------------------------------------------------------------
    output_dir = Path("results/my_first_sim_plots")
    save_all_plots(results, str(output_dir))
    print(f"\nCharts saved to: {output_dir}/")


if __name__ == "__main__":
    main()
