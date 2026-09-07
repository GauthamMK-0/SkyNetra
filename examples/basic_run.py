"""
basic_run.py — A complete SkyNetra simulation run file demonstrating both
the 3-line Quickstart API and the advanced FullConfig customization.

Run:  python examples/basic_run.py
"""

from __future__ import annotations

import skynetra as sn
from skynetra.interface.config.defaults import FullConfig


def quickstart_demo() -> None:
    """Mode 1: The 3-Line Quickstart API.

    Runs a full Walker-Delta LEO constellation (3 planes x 6 satellites = 18 sats)
    with 2 on-orbit compute pods, load-adaptive backpressure routing, space
    physics models, and Poisson inference query workloads with zero boilerplate.
    """
    print("=" * 70)
    print("           MODE 1: 3-LINE SKYNETRA QUICKSTART SIMULATION              ")
    print("=" * 70)

    # 1. Run simulation with intuitive keyword arguments
    results = sn.simulate(
        duration_s=60.0,
        constellation="3x6",
        pods=2,
        routing="backpressure",
        workload="inference",
        physics=True,
    )

    # 2. Print comprehensive, formatted terminal report directly
    results.report("QUICKSTART SIMULATION RESULTS")

    # 3. Export all 7 visualization plots in 1 call
    saved_plots = results.plot("results/basic_run_quickstart_plots")
    print(f"\nGenerated {len(saved_plots)} plots under results/basic_run_quickstart_plots/\n")


def advanced_config_demo() -> None:
    """Mode 2: Advanced Customization with FullConfig.

    For power users who need granular control over orbital inclination,
    ISL/GSL link capacities, elevation gating angles, and custom workloads.
    """
    print("=" * 70)
    print("           MODE 2: ADVANCED FULLCONFIG CUSTOMIZATION                  ")
    print("=" * 70)

    config = FullConfig(
        simulation={"duration_s": 120.0, "seed": 42, "record_events": True},
        constellation={
            "n_planes": 3,
            "sats_per_plane": 6,
            "altitude_km": 550.0,
            "inclination_deg": 53.0,
        },
        pods={"n_pods": 2},
        ground_stations={"n_ground_stations": 1, "gsl_elevation_min_deg": 10.0},
        network={"isl_capacity_gbps": 100.0, "gsl_capacity_gbps": 10.0},
        routing={"strategy": "backpressure"},
        physics={
            "thermal": {"enabled": True},
            "radiation": {"enabled": True},
            "power": {"enabled": True},
        },
        workload={
            "active": ["ai_training_sync", "inference_query"],
            "ai_training_sync": {
                "sync_interval_s": 15.0,
                "gradient_size_bytes": 10_000_000,
                "gradient_flops": 1e11,
            },
            "inference_query": {
                "mean_interval_s": 2.0,
                "query_size_bytes": 500,
                "flops_required": 1e9,
            },
        },
        metrics={
            "active": [
                "network_metrics",
                "compute_metrics",
                "physics_metrics",
                "topology_metrics",
            ]
        },
    )

    # Execute simulation directly via sn.simulate(config=config)
    results = sn.simulate(config=config)

    # Print dashboard
    results.report("ADVANCED FULLCONFIG SIMULATION RESULTS")

    # Access typed properties directly without manual dictionary unpacking
    print("\n[Direct Typed Property Inspection]")
    print(f"  * Delivery Rate      : {results.network.delivery_rate:.2f}%")
    print(f"  * Mean Latency       : {results.network.avg_latency_ms:.2f} ms")
    print(f"  * Total FLOPs Accrued: {results.compute.total_flops:.2e} FLOPS")
    print(f"  * Core Temperature   : {results.physics.avg_temperature_k:.1f} K")
    print(f"  * Active Vertices    : {results.topology.node_count} nodes")

    # Save visual figures
    results.plot("results/basic_run_advanced_plots")
    print("\nCharts saved to: results/basic_run_advanced_plots/\n")


def main() -> None:
    quickstart_demo()
    advanced_config_demo()


if __name__ == "__main__":
    main()
