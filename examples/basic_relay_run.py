"""
Minimal SkyNetra setup: satellite constellation relaying ground station
inference queries to an on-orbit compute pod via ISL mesh.

Demonstrates:
  - Constellation topology creation (2 planes x 3 satellites)
  - Ground-to-satellite access link (GSL) with elevation gating
  - Inter-satellite optical link (ISL) mesh routing
  - On-orbit compute pod task execution

Run:  python examples/basic_relay_run.py
"""

from __future__ import annotations

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation


def main() -> None:
    config = FullConfig(
        simulation={"duration_s": 60.0, "seed": 42},
        constellation={"n_planes": 2, "sats_per_plane": 3, "altitude_km": 550.0},
        ground_stations={"n_ground_stations": 1, "gsl_elevation_min_deg": 10.0},
        pods={"n_pods": 1},
        network={"isl_capacity_gbps": 100.0, "gsl_capacity_gbps": 10.0},
        routing={"strategy": "shortest_path"},
        workload={
            "active": ["inference_query"],
            "inference_query": {
                "mean_interval_s": 4.0,
                "query_size_bytes": 1024,
                "flops_required": 1e9,
            },
        },
        metrics={"active": ["network_metrics", "compute_metrics", "topology_metrics"]},
    )

    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    print(f"Basic Relay Simulation ({results.duration:.1f}s):")
    net = results.engine_metrics.get("network_metrics", {})
    comp = results.engine_metrics.get("compute_metrics", {})
    top = results.engine_metrics.get("topology_metrics", {})

    print(
        f"  Network  : transmitted={net.get('transmitted', 0)} | "
        f"delivered={net.get('delivered', 0)} | "
        f"dropped={net.get('dropped', 0)} | "
        f"avg_latency={net.get('avg_latency_s', 0.0) * 1000:.2f} ms"
    )
    print(
        f"  Compute  : jobs_completed={comp.get('compute_jobs_completed', 0)} | "
        f"total_flops={comp.get('compute_flops_completed', 0.0):.1e} FLOPS | "
        f"avg_service_time={comp.get('avg_compute_latency_s', 0.0) * 1000:.2f} ms"
    )
    print(
        f"  Topology : active_nodes={top.get('final_node_count', 0)} | "
        f"active_edges={top.get('final_edge_count', 0)} | "
        f"updates={top.get('topology_updates', 0)}"
    )


if __name__ == "__main__":
    main()
