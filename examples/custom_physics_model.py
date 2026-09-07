"""
How to write and use a custom `PhysicsModel` without touching the
`skynetra` source: `SolarFlareModel` adds radiation dose at a
configurable rate during flares.

It implements the two ABC methods (`compute_node_physics`,
`compute_link_physics`), gets registered in the L2 strategy registry,
and is wired into the run through the L3 `physics_specs` list.

Run:  python examples/custom_physics_model.py
"""

from __future__ import annotations

from typing import Any

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.foundation.types import NodeId, Vector3
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation


class SolarFlareModel(PhysicsModel):
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._flare_dose_rate = self._config.get("flare_dose_rate", 0.5)

    def compute_node_physics(
        self,
        node_id: NodeId,
        node: Node,
        sat_position: Vector3 | None,
        time_s: float,
        dt_s: float,
        constellation: ConstellationConfig,
    ) -> dict[str, Any]:
        return {
            "radiation_dose_rad": node.physics_state["radiation_dose_rad"]
            + self._flare_dose_rate * dt_s
        }

    def compute_link_physics(
        self,
        node_a: NodeId,
        node_b: NodeId,
        distance_km: float,
        time_s: float,
        dt_s: float,
    ) -> dict[str, Any]:
        return {"radiation_bit_error_rate": 1e-4}

    def name(self) -> str:
        return "solar_flare"


def main() -> None:
    STRATEGIES["solar_flare"] = SolarFlareModel

    config = FullConfig(
        simulation={"duration_s": 60.0, "seed": 42, "physics_tick_interval_s": 1.0},
        constellation={"n_planes": 2, "sats_per_plane": 3, "altitude_km": 550.0},
        pods={"n_pods": 2},
        ground_stations={"n_ground_stations": 1, "gsl_elevation_min_deg": 10.0},
        workload={
            "active": ["inference_query"],
            "inference_query": {"mean_interval_s": 4.0, "flops_required": 1e9},
        },
        metrics={"active": ["network_metrics", "compute_metrics", "physics_metrics"]},
    )
    spec = config_to_simulation_spec(config)
    spec.physics_specs = [
        {"name": "solar_flare", "config": {"enabled": True, "flare_dose_rate": 0.5}}
    ]

    print("Running Custom SolarFlareModel Simulation (60.0s)...")
    results = OrbitDCSimulation.from_spec(spec).run()

    net = results.engine_metrics.get("network_metrics", {})
    comp = results.engine_metrics.get("compute_metrics", {})
    phys = results.engine_metrics.get("physics_metrics", {})

    transmitted = net.get("transmitted", 0)
    delivered = net.get("delivered", 0)
    dropped = net.get("dropped", 0)
    avg_latency_ms = net.get("avg_latency_s", 0.0) * 1000
    loss_rate = (dropped / max(1, transmitted)) * 100
    delivery_rate = (delivered / max(1, delivered + dropped)) * 100

    print("\n" + "=" * 70)
    print("                SKYNETRA CUSTOM PHYSICS MODEL REPORT                  ")
    print("=" * 70)
    print("Physics Extension Configuration:")
    print("  * Active Plugin Model : SolarFlareModel (Custom Layer 2 Implementation)")
    print("  * Solar Flare Event   : Active throughout simulation (60.0 simulated seconds)")
    print("  * Flare Dose Rate     : 0.50 rad(Si)/s applied to all constellation nodes")
    print("  * Injected Link BER   : 1.0e-04 optical bit error rate on all ISL/GSL channels")
    print("  * Constellation Scale : 6 Satellites (2 planes x 3 sats), 2 Pods, 1 Ground Station")

    print("\n[Space Environmental State & Degradation]")
    print(f"  * Registered Physics Models    : {phys.get('active_models', ['SolarFlareModel'])}")
    print(f"  * Single Event Latchup Faults  : {phys.get('radiation_fault_events', 0)} events")
    print(f"  * Physics-Induced Link Drops   : {phys.get('physics_caused_drops', 0)} drops")
    print(f"  * Thermal Throttle Events      : {phys.get('thermal_throttle_events', 0)} events")

    print("\n[Degraded Space Network Performance]")
    print(f"  * Packets Injected/Transmitted : {transmitted}")
    print(f"  * Packets Successfully Received: {delivered}")
    print(f"  * Total Lost/Dropped Packets   : {dropped}")
    print(f"  * Network Packet Loss Rate     : {loss_rate:.2f}%")
    print(f"  * Delivery Completion Rate     : {delivery_rate:.2f}%")
    print(f"  * Mean End-to-End Latency      : {avg_latency_ms:.2f} ms")

    print("\n[On-Orbit Compute Accelerator Servicing]")
    print(f"  * Inference Tasks Finished     : {comp.get('compute_jobs_completed', 0)} tasks")
    comp_flops = comp.get('compute_flops_completed', 0.0)
    print(f"  * Total Compute FLOPs Accrued  : {comp_flops:.2e} FLOPS")
    comp_lat_ms = comp.get('avg_compute_latency_s', 0.0) * 1000
    print(f"  * Mean Task Service Time       : {comp_lat_ms:.2f} ms")
    print("=" * 70)


if __name__ == "__main__":
    main()
