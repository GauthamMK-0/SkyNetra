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

    print("Running Basic Relay Simulation (60.0s)...")
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    net = results.engine_metrics.get("network_metrics", {})
    comp = results.engine_metrics.get("compute_metrics", {})
    top = results.engine_metrics.get("topology_metrics", {})

    transmitted = net.get("transmitted", 0)
    delivered = net.get("delivered", 0)
    dropped = net.get("dropped", 0)
    avg_latency_ms = net.get("avg_latency_s", 0.0) * 1000
    loss_rate = (dropped / max(1, transmitted)) * 100
    delivery_rate = (delivered / max(1, delivered + dropped)) * 100

    print("\n" + "=" * 70)
    print("                 SKYNETRA BASIC RELAY SIMULATION                     ")
    print("=" * 70)
    print("Scenario Architecture:")
    print("  * Constellation       : Walker-Delta 2 planes x 3 satellites (6 total @ 550 km)")
    print("  * Space Infrastructure: 1 Dedicated On-Orbit Compute Pod (pod-1)")
    print("  * Terrestrial Segment : 1 Ground Station (gs-1, >= 10.0 deg elevation mask)")
    print("  * Inter-Satellite Link: Optical ISL mesh (100.0 Gbps capacity)")
    print("  * Ground-Satellite Link: Ka-Band GSL access link (10.0 Gbps capacity)")
    print(f"  * Simulation Horizon  : {results.duration:.1f} simulated seconds")

    print("\n[Network Forwarding & Delivery]")
    print(f"  * Packets Injected/Transmitted : {transmitted} queries")
    print(f"  * Successfully Relayed to Pod  : {delivered} queries")
    print(f"  * Packets Dropped (Unreachable): {dropped} packets")
    print(f"  * Packet Loss Rate             : {loss_rate:.2f}%")
    print(f"  * Delivery Success Rate        : {delivery_rate:.2f}%")
    print(f"  * Mean End-to-End Latency      : {avg_latency_ms:.2f} ms")

    print("\n[On-Orbit Compute Accelerator (Pod-1)]")
    print(f"  * Inference Tasks Processed    : {comp.get('compute_jobs_completed', 0)} tasks")
    comp_flops = comp.get('compute_flops_completed', 0.0)
    print(f"  * Total Workload FLOPs Accrued : {comp_flops:.2e} FLOPS")
    comp_lat_ms = comp.get('avg_compute_latency_s', 0.0) * 1000
    print(f"  * Mean Task Compute Latency    : {comp_lat_ms:.2f} ms")

    print("\n[Constellation Topology & Dynamics]")
    print(f"  * Total Network Vertices       : {top.get('final_node_count', 0)} nodes")
    print(f"  * Active Dynamic ISL/GSL Edges : {top.get('final_edge_count', 0)} directed links")
    print(f"  * Periodic Topology Recomputes : {top.get('topology_updates', 0)} updates")
    print("=" * 70)


if __name__ == "__main__":
    main()
