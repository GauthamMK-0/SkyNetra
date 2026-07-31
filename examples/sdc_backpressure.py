from __future__ import annotations

from typing import Dict, List

from skynetra.domain.nodes import GroundStation, PhysicsState, PodNode, RelayNode
from skynetra.engines.physics import PhysicsOrchestrator, RadiationModel, ThermalModel
from skynetra.engines.routing import BackPressureRouter
from skynetra.engines.workload import AITrainingWorkload, WorkloadProfile
from skynetra.foundation.types import NodeId
from skynetra.orchestration.engine import SkyNetraSimulation
from skynetra.orchestration.metrics import (
    ComputeMetricsCollector,
    NetworkMetricsCollector,
    PhysicsMetricsCollector,
    TopologyMetricsCollector,
)


def main() -> None:
    nodes: Dict[NodeId, RelayNode | PodNode | GroundStation] = {
        NodeId("relay-1"): RelayNode(NodeId("relay-1")),
        NodeId("relay-2"): RelayNode(NodeId("relay-2")),
        NodeId("pod-1"): PodNode(NodeId("pod-1"), flops=2e12, memory_gb=32.0),
        NodeId("pod-2"): PodNode(NodeId("pod-2"), flops=4e12, memory_gb=64.0),
        NodeId("gs-1"): GroundStation(NodeId("gs-1")),
    }

    for node in nodes.values():
        node.physics = PhysicsState(
            temperature=290.0,
            radiation_dose=0.0,
            power_available=500.0,
            power_consumed=100.0,
        )

    router = BackPressureRouter()
    router.update_backlog("relay-1->relay-2", 10.0)
    router.update_backlog("relay-2->pod-1", 5.0)
    router.update_backlog("relay-1->pod-1", 2.0)

    physics_models: List = [
        ThermalModel(albedo=0.3, emissivity=0.8),
        RadiationModel(background_dose_rate=0.01),
    ]
    orchestrator = PhysicsOrchestrator(physics_models)

    profile = WorkloadProfile(
        name="sdc-training",
        packet_size_bytes=1500,
        generation_rate=2.0,
        ttl=64,
    )
    workload = AITrainingWorkload(profile)

    collectors = [
        NetworkMetricsCollector(),
        TopologyMetricsCollector(),
        PhysicsMetricsCollector(),
        ComputeMetricsCollector(),
    ]

    sim = SkyNetraSimulation(
        nodes=nodes,
        routing_engine=router,
        physics_orchestrator=orchestrator,
        workload_generators=[workload],
        metrics_collectors=collectors,
        dt=1.0,
    )

    results = sim.run(duration=100.0)

    print(f"SDC BackPressure simulation: {results.duration}s")
    for name, data in results.metrics.items():
        print(f"  {name}: {data}")


if __name__ == "__main__":
    main()
