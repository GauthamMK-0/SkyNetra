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
        return {}

    def name(self) -> str:
        return "solar_flare"


def main() -> None:
    STRATEGIES["solar_flare"] = SolarFlareModel

    config = FullConfig(
        simulation={"duration_s": 60.0, "seed": 42, "physics_tick_interval_s": 1.0},
        constellation={"n_planes": 1, "sats_per_plane": 3},
        pods={"n_pods": 0},
        workload={"active": []},
        metrics={"active": ["physics_metrics"]},
    )
    spec = config_to_simulation_spec(config)
    spec.physics_specs = [
        {"name": "solar_flare", "config": {"enabled": True, "flare_dose_rate": 0.8}}
    ]

    results = OrbitDCSimulation.from_spec(spec).run()

    print(f"SolarFlareModel simulation: {results.duration}s")
    print(f"Metrics: {results.engine_metrics}")


if __name__ == "__main__":
    main()
