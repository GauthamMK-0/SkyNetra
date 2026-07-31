"""
Orchestration layer (L3) — SkyNetraSimulation: SimPy core loop.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

import simpy
from simpy.events import Timeout

from skynetra.domain.nodes.base import Node
from skynetra.domain.topology.graph import build_topology_graph
from skynetra.domain.topology.isl import link_quality
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId, TimeSeconds
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.events import (
    PacketEvent,
    PhysicsEvent,
    SimulationEndEvent,
    SimulationStartEvent,
    TopologyEvent,
)
from skynetra.orchestration.metrics.aggregator import MetricsAggregator
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.results import SimulationResults


class SkyNetraSimulation:
    def __init__(
        self,
        nodes: Dict[NodeId, Node],
        routing_engine: RoutingEngine,
        physics_orchestrator: Optional[PhysicsOrchestrator] = None,
        workload_generators: Optional[List[WorkloadGenerator]] = None,
        metrics_collectors: Optional[List[MetricsCollector]] = None,
        dt: float = 1.0,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._context = SimulationContext(
            nodes=nodes,
            routing_engine=routing_engine,
            physics_orchestrator=physics_orchestrator or PhysicsOrchestrator([]),
            workload_generators=workload_generators or [],
            event_bus=event_bus or EventBus(),
            current_time=0.0,
            dt=dt,
        )
        self._metrics_aggregator = MetricsAggregator(metrics_collectors or [])
        self._results: Optional[SimulationResults] = None

    def run(self, duration: float) -> SimulationResults:
        env = simpy.Environment()
        self._context.current_time = 0.0

        self._context.event_bus.publish(
            SimulationStartEvent(time=TimeSeconds(0.0), event_type="simulation_start")
        )

        env.process(self._sim_loop(env, duration))
        env.run(until=duration)

        self._context.event_bus.publish(
            SimulationEndEvent(
                time=TimeSeconds(duration), event_type="simulation_end", total_duration=duration
            )
        )

        self._results = SimulationResults(
            metrics=self._metrics_aggregator.collect(self._context),
            events=[],
            duration=duration,
        )
        return self._results

    def _sim_loop(self, env: simpy.Environment, duration: float) -> Generator[Any, None, None]:
        while env.now < duration:
            t = env.now
            self._context.current_time = t

            self._step_physics(t)
            self._step_topology(t)
            self._step_routing(t)
            self._step_workload(t)
            self._step_metrics(t)

            yield Timeout(env, self._context.dt)

    def _step_physics(self, t: float) -> None:
        if self._context.physics_orchestrator:
            states = {
                nid: node.physics for nid, node in self._context.nodes.items()
            }
            updated = self._context.physics_orchestrator.apply(states, self._context.dt)
            for nid, state in updated.items():
                if nid in self._context.nodes:
                    self._context.nodes[nid].physics = state
                self._context.event_bus.publish(
                    PhysicsEvent(
                        time=TimeSeconds(t),
                        event_type="physics_update",
                        node_id=nid,
                        temperature=state.temperature,
                        radiation_dose=state.radiation_dose,
                        power_available=state.power_available,
                    )
                )

    def _step_topology(self, t: float) -> None:
        positions = {
            nid: node.physics.position for nid, node in self._context.nodes.items()
        }
        self._context.topology_graph = build_topology_graph(
            positions=positions,
            quality_fn=lambda a, b, pa, pb: link_quality(pa, pb),
            threshold=0.01,
        )
        self._context.event_bus.publish(
            TopologyEvent(
                time=TimeSeconds(t),
                event_type="topology_update",
                edge_count=self._context.topology_graph.number_of_edges(),
                node_count=self._context.topology_graph.number_of_nodes(),
            )
        )

    def _step_routing(self, t: float) -> None:
        pass

    def _step_workload(self, t: float) -> None:
        for gen in self._context.workload_generators:
            packets = gen.generate(
                TimeSeconds(t), {nid: node for nid, node in self._context.nodes.items()}
            )
            for pkt in packets:
                self._context.event_bus.publish(
                    PacketEvent(
                        time=TimeSeconds(t), event_type="packet_generated",
                        packet=pkt, status="generated",
                    )
                )

    def _step_metrics(self, t: float) -> None:
        self._metrics_aggregator.collect(self._context)

    @classmethod
    def from_layers(
        cls,
        nodes: Dict[NodeId, Node],
        routing_engine: RoutingEngine,
        physics_orchestrator: Optional[PhysicsOrchestrator] = None,
        workload_generators: Optional[List[WorkloadGenerator]] = None,
        metrics_collectors: Optional[List[MetricsCollector]] = None,
        dt: float = 1.0,
    ) -> SkyNetraSimulation:
        return cls(
            nodes=nodes,
            routing_engine=routing_engine,
            physics_orchestrator=physics_orchestrator,
            workload_generators=workload_generators,
            metrics_collectors=metrics_collectors,
            dt=dt,
        )
