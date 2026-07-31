from __future__ import annotations

from typing import Dict, List

from skynetra.foundation.types import NodeId
from skynetra.domain.nodes import RelayNode, PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES
from skynetra.engines.physics import PhysicsOrchestrator
from skynetra.engines.routing import ShortestPathRouter
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics import PhysicsMetricsCollector


class SolarFlareModel(PhysicsModel):
    def __init__(self, flare_dose_rate: float = 0.5) -> None:
        self._flare_dose_rate = flare_dose_rate

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        new_states = {}
        for nid, state in states.items():
            new_states[nid] = PhysicsState(
                position=state.position,
                velocity=state.velocity,
                temperature=state.temperature,
                radiation_dose=state.radiation_dose + self._flare_dose_rate * dt,
                power_available=state.power_available,
                power_consumed=state.power_consumed,
            )
        return new_states

    def name(self) -> str:
        return "solar_flare"


def main() -> None:
    STRATEGIES["solar_flare"] = SolarFlareModel

    nodes: Dict[NodeId, RelayNode] = {
        NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        NodeId("sat-2"): RelayNode(NodeId("sat-2")),
    }
    for node in nodes.values():
        node.physics = PhysicsState(
            temperature=300.0,
            radiation_dose=0.0,
            power_available=100.0,
        )

    flare_model = SolarFlareModel(flare_dose_rate=0.8)
    orchestrator = PhysicsOrchestrator([flare_model])

    router = ShortestPathRouter()
    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        physics_orchestrator=orchestrator,
        metrics_collectors=[PhysicsMetricsCollector()],
        dt=1.0,
    )
    results = sim.run(duration=5.0)

    print(f"SolarFlareModel simulation: {results.duration}s")
    print(f"Metrics: {results.metrics}")
    for nid, node in nodes.items():
        print(f"  {nid}: radiation_dose={node.physics.radiation_dose:.2f}")


if __name__ == "__main__":
    main()
