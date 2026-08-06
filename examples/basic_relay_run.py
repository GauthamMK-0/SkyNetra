"""
Minimal SkyNetra setup: three relay satellites and one ground station,
shortest-path routing, no physics, no workloads.

Run:  python examples/basic_relay_run.py
"""

from __future__ import annotations

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation


def main() -> None:
    config = FullConfig(
        simulation={"duration_s": 30.0, "seed": 42},
        constellation={"n_planes": 1, "sats_per_plane": 3},
        ground_stations={"n_ground_stations": 1},
        pods={"n_pods": 0},
        workload={"active": []},
        metrics={"active": ["network_metrics", "topology_metrics"]},
    )

    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    print(f"Basic relay simulation: {results.duration}s")
    for name, data in results.engine_metrics.items():
        print(f"  {name}: {data}")


if __name__ == "__main__":
    main()
