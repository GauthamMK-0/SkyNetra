"""
Orchestration layer (L3) — OrbitDCSimulation: the SimPy core loop.

The engine owns the simulation time loop. Layer 2 components (routing,
physics, workloads) are pure computations or generators; this module
wraps them in SimPy processes:

  * `_topology_update_loop`  — refresh satellite positions, rebuild the
    Layer 1 graph, notify the routing engine, bump `topology_version`.
  * `_physics_tick_loop`     — run the enabled physics models, apply
    node/link updates to the live registry and graph, store routing
    weight overrides on the context.
  * `_metrics_snapshot_loop` — record periodic metric snapshots into
    the context scratchpad.
  * per-workload processes   — call `WorkloadGenerator.generate(env,
    publish_packet, node_registry)`; each published packet is forwarded
    hop-by-hop by its own `_forward_packet` process.

Any exception raised by a Layer 2 component is caught, reported as an
`EngineErrorEvent`, and the simulation continues.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Generator

import networkx as nx
import simpy

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import PropagatorInterface, ReferenceCircularPropagator
from skynetra.domain.packets.packet import Packet
from skynetra.domain.topology.graph import build_topology_graph
from skynetra.domain.topology.isl import EARTH_RADIUS_KM, compute_isl_link_quality
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.registry import build_physics_models
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import get_routing_engine
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.registry import build_workloads
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.math_utils import rotate_vector_z, sidereal_angle_rad
from skynetra.foundation.types import LinkId, NodeId, Vector3
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.events import (
    ComputeJobCompleteEvent,
    EngineErrorEvent,
    PacketArrivalEvent,
    PacketDeliveredEvent,
    PacketDropEvent,
    PacketTransmitEvent,
    PhysicsInducedDropEvent,
    PhysicsTickEvent,
    RoutingDecisionEvent,
    SimulationEvent,
    TopologyUpdateEvent,
)
from skynetra.orchestration.metrics.aggregator import MetricsAggregator
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.registry import build_metrics_collectors
from skynetra.orchestration.results import SimulationResults

# Per-packet hop cap. Shortest-path routes are simple paths (bounded by
# node count); the generous headroom lets load-adaptive routers (whose
# greedy per-hop decisions may wander through congestion) finish their
# search on large constellations instead of dying mid-flood.
MAX_FORWARD_HOPS = 256
METRICS_SNAPSHOT_INTERVAL_S = 1.0
POD_ATTACH_NEAREST_SATS = 2


class SkyNetraSimulation:
    """SimPy-based orchestration core for a low-Earth-orbit data center.

    Construct via `from_spec` (everything derived from a spec) or
    `from_layers` (caller-provided node registry and Layer 2 engines),
    then `setup()` for the live context and `run()` for the results.
    """

    @dataclass
    class SimulationSpec:
        constellation: ConstellationConfig
        n_pods: int = 1
        n_ground_stations: int = 1
        routing_strategy: str = "shortest_path"
        routing_config: dict[str, Any] = field(default_factory=dict)
        physics_specs: list[dict[str, Any]] = field(default_factory=list)
        workload_specs: list[dict[str, Any]] = field(default_factory=list)
        metrics_specs: list[dict[str, Any]] = field(default_factory=list)
        sim_duration_s: float = 60.0
        topology_update_interval_s: float = 10.0
        physics_tick_interval_s: float = 1.0
        isl_capacity_gbps: float = 100.0
        gsl_capacity_gbps: float = 10.0
        gsl_elevation_min_deg: float = 10.0
        seed: int = 42
        record_events: bool = True
        max_event_log_size: int | None = None

    def __init__(
        self,
        constellation: ConstellationConfig,
        node_registry: dict[NodeId, Node],
        routing_engine: RoutingEngine,
        physics_orchestrator: PhysicsOrchestrator | None = None,
        workloads: list[WorkloadGenerator] | None = None,
        metrics_collectors: list[MetricsCollector] | None = None,
        sim_duration_s: float = 60.0,
        topology_update_interval_s: float = 10.0,
        physics_tick_interval_s: float = 1.0,
        isl_capacity_gbps: float = 100.0,
        gsl_capacity_gbps: float = 10.0,
        gsl_elevation_min_deg: float = 10.0,
        seed: int = 42,
        debug_routing: bool = False,
        record_events: bool = True,
        max_event_log_size: int | None = None,
    ) -> None:
        self._constellation = constellation
        self._propagator: PropagatorInterface = ReferenceCircularPropagator()
        self._node_registry = node_registry
        self._routing_engine = routing_engine
        self._physics_orchestrator = physics_orchestrator or PhysicsOrchestrator([])
        self._workloads = workloads or []
        self._metrics_collectors = self._resolve_collectors(metrics_collectors)
        self._sim_duration_s = sim_duration_s
        self._topology_update_interval_s = topology_update_interval_s
        self._physics_tick_interval_s = physics_tick_interval_s
        self._isl_capacity_gbps = isl_capacity_gbps
        self._gsl_capacity_gbps = gsl_capacity_gbps
        self._gsl_elevation_min_deg = gsl_elevation_min_deg
        self._seed = seed
        self._debug_routing = debug_routing
        self._record_events = record_events
        self._max_event_log_size = max_event_log_size
        self._context: SimulationContext | None = None
        self._event_log: list[SimulationEvent] = []
        self._initial_station_positions: dict[NodeId, Vector3] | None = None

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> OrbitDCSimulation:
        """Build a full simulation from a spec (nodes derived from the
        constellation geometry)."""
        propagator = ReferenceCircularPropagator()
        node_registry: dict[NodeId, Node] = {}
        for sat_id in propagator.get_sat_ids(spec.constellation):
            node_registry[sat_id] = RelayNode(sat_id)
        for i in range(1, spec.n_pods + 1):
            node_registry[NodeId(f"pod-{i}")] = PodNode(NodeId(f"pod-{i}"))
        for i in range(1, spec.n_ground_stations + 1):
            node_registry[NodeId(f"gs-{i}")] = GroundStationNode(NodeId(f"gs-{i}"))

        collectors = build_metrics_collectors(spec.metrics_specs) if spec.metrics_specs else []

        return cls(
            constellation=spec.constellation,
            node_registry=node_registry,
            routing_engine=get_routing_engine(spec.routing_strategy, spec.routing_config),
            physics_orchestrator=PhysicsOrchestrator(build_physics_models(spec.physics_specs)),
            workloads=build_workloads(spec.workload_specs),
            metrics_collectors=collectors,
            sim_duration_s=spec.sim_duration_s,
            topology_update_interval_s=spec.topology_update_interval_s,
            physics_tick_interval_s=spec.physics_tick_interval_s,
            isl_capacity_gbps=spec.isl_capacity_gbps,
            gsl_capacity_gbps=spec.gsl_capacity_gbps,
            gsl_elevation_min_deg=spec.gsl_elevation_min_deg,
            seed=spec.seed,
            record_events=spec.record_events,
            max_event_log_size=spec.max_event_log_size,
        )

    @classmethod
    def from_layers(
        cls,
        constellation: ConstellationConfig,
        node_registry: dict[NodeId, Node],
        routing_engine: RoutingEngine,
        physics_orchestrator: PhysicsOrchestrator | None = None,
        workloads: list[WorkloadGenerator] | None = None,
        metrics_collectors: list[MetricsCollector] | None = None,
        sim_duration_s: float = 60.0,
        topology_update_interval_s: float = 10.0,
        physics_tick_interval_s: float = 1.0,
        isl_capacity_gbps: float = 100.0,
        gsl_capacity_gbps: float = 10.0,
        gsl_elevation_min_deg: float = 10.0,
        seed: int = 42,
        record_events: bool = True,
        max_event_log_size: int | None = None,
    ) -> OrbitDCSimulation:
        """Build a simulation from caller-provided Layer 1/2 objects."""
        return cls(
            constellation=constellation,
            node_registry=node_registry,
            routing_engine=routing_engine,
            physics_orchestrator=physics_orchestrator,
            workloads=workloads,
            metrics_collectors=metrics_collectors,
            sim_duration_s=sim_duration_s,
            topology_update_interval_s=topology_update_interval_s,
            physics_tick_interval_s=physics_tick_interval_s,
            isl_capacity_gbps=isl_capacity_gbps,
            gsl_capacity_gbps=gsl_capacity_gbps,
            gsl_elevation_min_deg=gsl_elevation_min_deg,
            seed=seed,
            record_events=record_events,
            max_event_log_size=max_event_log_size,
        )

    @staticmethod
    def _resolve_collectors(
        collectors: list[MetricsCollector] | None,
    ) -> list[MetricsCollector]:
        resolved = list(collectors) if collectors is not None else []
        if not any(c.name == "network_metrics" for c in resolved):
            resolved.append(NetworkMetricsCollector())
        return resolved

    # ------------------------------------------------------------------
    # Setup / run
    # ------------------------------------------------------------------

    def setup(self) -> SimulationContext:
        """Assemble the live `SimulationContext` (idempotent)."""
        if self._context is not None:
            return self._context

        if self._initial_station_positions is None:
            self._initial_station_positions = self._initial_station_positions_for(
                self._node_registry
            )

        env = simpy.Environment()
        event_bus = EventBus()
        graph = self._build_graph(self._node_registry, time_s=0.0)
        self._routing_engine.update_topology(graph)
        aggregator = MetricsAggregator(self._metrics_collectors, event_bus)

        pod_ids = [nid for nid, node in self._node_registry.items() if node.node_type == "pod"]
        ground_station_ids = [
            nid for nid, node in self._node_registry.items() if node.node_type == "ground"
        ]

        context = SimulationContext(
            env=env,
            event_bus=event_bus,
            node_registry=self._node_registry,
            graph=graph,
            routing_engine=self._routing_engine,
            physics_orchestrator=self._physics_orchestrator,
            metrics_aggregator=aggregator,
            sim_duration_s=self._sim_duration_s,
            topology_update_interval_s=self._topology_update_interval_s,
            physics_tick_interval_s=self._physics_tick_interval_s,
            seed=self._seed,
            constellation=self._constellation,
            propagator=self._propagator,
            pod_ids=pod_ids,
            ground_station_ids=ground_station_ids,
            debug_routing=self._debug_routing,
            scratchpad={
                "sim_duration_s": self._sim_duration_s,
                "seed": self._seed,
                "metrics_snapshots": [],
            },
        )
        for pod_id in pod_ids:
            context.compute_stores[pod_id] = simpy.Store(env)
        self._context = context
        return context

    def run(self) -> SimulationResults:
        """Run the simulation for `sim_duration_s` and return results."""
        context = self.setup()
        random.seed(context.seed)

        context.env.process(self._topology_update_loop(context))
        if context.physics_orchestrator is not None and context.physics_orchestrator.models:
            context.env.process(self._physics_tick_loop(context))
        for workload in self._workloads:
            context.env.process(self._safe_workload(context, workload))
        for pod_id in context.pod_ids:
            context.env.process(self._compute_loop(context, pod_id))
        context.env.process(self._metrics_snapshot_loop(context))

        context.env.run(until=context.sim_duration_s)
        context.current_time_s = context.sim_duration_s
        context.scratchpad["topology_version"] = context.topology_version

        aggregator = context.metrics_aggregator
        engine_metrics = aggregator.get_all_summaries() if aggregator is not None else {}
        return SimulationResults(
            engine_metrics=engine_metrics,
            events=list(self._event_log),
            duration=context.sim_duration_s,
        )

    # ------------------------------------------------------------------
    # Topology construction
    # ------------------------------------------------------------------

    def _build_graph(self, node_registry: dict[NodeId, Node], time_s: float) -> nx.DiGraph:
        positions_all = self._propagator.get_positions(time_s, self._constellation)
        sat_ids = [
            sat_id
            for sat_id in self._propagator.get_sat_ids(self._constellation)
            if sat_id in node_registry
        ]
        sat_positions = {sid: positions_all[sid] for sid in sat_ids}

        pod_ids = [nid for nid, n in node_registry.items() if n.node_type == "pod"]
        gs_ids = [nid for nid, n in node_registry.items() if n.node_type == "ground"]
        # Ground stations (and pods, modeled as co-located ground-like
        # facilities) are Earth-fixed: rotate their initial inertial
        # positions by the sidereal angle at `time_s`.
        rotation_rad = sidereal_angle_rad(time_s)
        if self._initial_station_positions is None:
            self._initial_station_positions = self._initial_station_positions_for(
                node_registry
            )
        station_positions = {
            nid: rotate_vector_z(pos, rotation_rad)
            for nid, pos in self._initial_station_positions.items()
        }
        gs_positions = {nid: station_positions[nid] for nid in gs_ids}

        graph = build_topology_graph(
            sat_positions=sat_positions,
            isl_links=self._isl_links(sat_ids, self._constellation),
            pod_ids=pod_ids,
            ground_stations=gs_positions,
            link_capacity_gbps=self._isl_capacity_gbps,
            gsl_capacity_gbps=self._gsl_capacity_gbps,
            gsl_elevation_min_deg=self._gsl_elevation_min_deg,
        )
        self._attach_pod_edges(
            graph,
            pod_ids,
            sat_positions,
            station_positions,
            capacity_gbps=self._gsl_capacity_gbps,
        )
        return graph

    @staticmethod
    def _isl_links(
        sat_ids: list[NodeId], constellation: ConstellationConfig
    ) -> list[tuple[NodeId, NodeId]]:
        """Deterministic ISL set: intra-plane rings plus inter-plane
        links between same-index satellites of adjacent planes."""
        if not sat_ids:
            return []
        planes = constellation.n_planes
        sats_per_plane = constellation.sats_per_plane
        if len(sat_ids) != planes * sats_per_plane:
            return list(zip(sat_ids, sat_ids[1:] + sat_ids[:1]))
        links: set[tuple[NodeId, NodeId]] = set()
        for plane in range(planes):
            for sat in range(sats_per_plane):
                a = sat_ids[plane * sats_per_plane + sat]
                b = sat_ids[plane * sats_per_plane + (sat + 1) % sats_per_plane]
                links.add((a, b))
        for sat in range(sats_per_plane):
            for plane in range(planes):
                a = sat_ids[plane * sats_per_plane + sat]
                b = sat_ids[((plane + 1) % planes) * sats_per_plane + sat]
                if a != b:
                    links.add((a, b))
        return sorted(links)

    @staticmethod
    def _station_position(index: int, count: int) -> Vector3:
        """Initial Earth-fixed position of station `index` of `count`."""
        angle = 2.0 * math.pi * index / max(count, 1)
        return (
            EARTH_RADIUS_KM * math.cos(angle),
            EARTH_RADIUS_KM * math.sin(angle),
            0.0,
        )

    def _initial_station_positions_for(
        self, node_registry: dict[NodeId, Node]
    ) -> dict[NodeId, Vector3]:
        """Earth-fixed initial positions of every ground station and pod.

        Computed once per node registry (deterministic); `_build_graph`
        rotates these into the inertial frame at each topology update.
        Pods and ground stations are each indexed by their own type so
        placement matches the pre-rotation geometry at t=0.
        """
        positions: dict[NodeId, Vector3] = {}
        pods = [nid for nid, n in node_registry.items() if n.node_type == "pod"]
        for index, nid in enumerate(pods):
            positions[nid] = self._station_position(index, max(len(pods), 1))
        gs = [nid for nid, n in node_registry.items() if n.node_type == "ground"]
        for index, nid in enumerate(gs):
            positions[nid] = self._station_position(index, max(len(gs), 1))
        return positions

    @staticmethod
    def _attach_pod_edges(
        graph: nx.DiGraph,
        pod_ids: list[NodeId],
        sat_positions: dict[NodeId, Vector3],
        pod_positions: dict[NodeId, Vector3],
        nearest: int = POD_ATTACH_NEAREST_SATS,
        capacity_gbps: float = 10.0,
    ) -> None:
        """Attach each pod to its `nearest` satellites (pods have no
        incident edges in the Layer 1 graph builder)."""
        for pod_id in pod_ids:
            pod_pos = pod_positions[pod_id]
            ranked = sorted(
                sat_positions.items(),
                key=lambda item: math.dist(pod_pos, item[1]),
            )
            for sat_id, sat_pos in ranked[:nearest]:
                distance_km = math.dist(pod_pos, sat_pos)
                quality = compute_isl_link_quality(pod_pos, sat_pos, distance_km)
                quality["capacity"] = capacity_gbps
                graph.add_edge(pod_id, sat_id, **quality)
                graph.add_edge(sat_id, pod_id, **quality)

    # ------------------------------------------------------------------
    # SimPy processes
    # ------------------------------------------------------------------

    def _topology_update_loop(self, context: SimulationContext) -> Generator[Any, None, None]:
        env = context.env
        while True:
            yield env.timeout(context.topology_update_interval_s)
            context.current_time_s = env.now
            context.graph = self._build_graph(context.node_registry, env.now)
            if context.routing_engine is not None:
                context.routing_engine.update_topology(context.graph)
            context.topology_version += 1
            self._publish(
                context,
                TopologyUpdateEvent(
                    time=env.now,
                    event_type="topology_update",
                    topology_version=context.topology_version,
                    edge_count=context.graph.number_of_edges(),
                    node_count=context.graph.number_of_nodes(),
                ),
            )

    def _physics_tick_loop(self, context: SimulationContext) -> Generator[Any, None, None]:
        env = context.env
        tick = 0
        while True:
            yield env.timeout(context.physics_tick_interval_s)
            context.current_time_s = env.now
            tick += 1
            orchestrator = context.physics_orchestrator
            if orchestrator is None or context.propagator is None or context.constellation is None:
                continue
            positions = context.propagator.get_positions(env.now, context.constellation)
            try:
                result = orchestrator.run_tick(
                    env.now,
                    context.physics_tick_interval_s,
                    context.graph,
                    context.node_registry,
                    positions,
                    context.constellation,
                )
            except Exception as exc:
                self._publish(
                    context,
                    EngineErrorEvent(
                        time=env.now,
                        event_type="engine_error",
                        component="physics",
                        error=str(exc),
                    ),
                )
                continue
            for node_id, delta in result["node_updates"].items():
                node = context.node_registry.get(node_id)
                if node is not None:
                    node.update_physics(delta)
            for (node_a, node_b), attrs in result["link_updates"].items():
                if context.graph.has_edge(node_a, node_b):
                    context.graph.edges[node_a, node_b].update(attrs)
            context.combined_weight_overrides = result["weight_overrides"]
            active_models = [model.__class__.__name__ for model in orchestrator.models]
            self._publish(
                context,
                PhysicsTickEvent(
                    time=env.now,
                    event_type="physics_tick",
                    tick=tick,
                    node_state={
                        nid: {
                            "physics_state": dict(node.physics_state),
                            "metrics_state": dict(node.metrics_state),
                        }
                        for nid, node in context.node_registry.items()
                    },
                    active_models=active_models,
                ),
            )

    def _metrics_snapshot_loop(self, context: SimulationContext) -> Generator[Any, None, None]:
        env = context.env
        while True:
            yield env.timeout(METRICS_SNAPSHOT_INTERVAL_S)
            aggregator = context.metrics_aggregator
            metrics = aggregator.get_all_summaries() if aggregator is not None else {}
            snapshots = context.scratchpad.setdefault("metrics_snapshots", [])
            snapshots.append({"time": env.now, "metrics": metrics})

    def _safe_workload(
        self, context: SimulationContext, workload: WorkloadGenerator
    ) -> Generator[Any, None, None]:
        def publish_packet(packet: Packet) -> None:
            context.env.process(self._forward_packet(packet, packet.src, context))

        try:
            yield from workload.generate(context.env, publish_packet, context.node_registry)
        except Exception as exc:
            self._publish(
                context,
                EngineErrorEvent(
                    time=context.env.now,
                    event_type="engine_error",
                    component="workload",
                    error=str(exc),
                ),
            )

    def _compute_loop(
        self, context: SimulationContext, pod_id: NodeId
    ) -> Generator[Any, None, None]:
        """Per-pod compute server: drains the pod's task queue with a
        service time of `flops_required / available_compute_flops()`.

        Woken by a token placed in the pod's `simpy.Store` on delivery;
        the task itself is dispatched from the pod's queue via
        `take_next_task` so the pod queue (read by load-aware routing)
        reflects true pending backlog.
        """
        env = context.env
        store = context.compute_stores.get(pod_id)
        pod = context.node_registry.get(pod_id)
        if store is None or not isinstance(pod, PodNode):
            return
        while True:
            yield store.get()
            task = pod.take_next_task()
            if task is None:
                continue
            service_s = task.flops_required / max(pod.available_compute_flops(), 1.0)
            yield env.timeout(service_s)
            pod.record_compute(task)
            self._publish(
                context,
                ComputeJobCompleteEvent(
                    time=env.now,
                    event_type="compute_job_complete",
                    node_id=pod_id,
                    packet=task,
                    compute_latency_s=max(0.0, env.now - task.created_at),
                ),
            )

    # ------------------------------------------------------------------
    # Packet forwarding
    # ------------------------------------------------------------------

    def _forward_packet(
        self,
        packet: Packet,
        current_node_id: NodeId,
        context: SimulationContext,
    ) -> Generator[Any, None, None]:
        env = context.env
        registry = context.node_registry
        current = registry.get(current_node_id)
        if current is None or not current.process_packet(packet):
            self._drop(context, packet, current_node_id, "source_unavailable")
            return

        packet.hops = 0
        packet.path_history = [str(current_node_id)]
        self._publish(
            context,
            PacketArrivalEvent(
                time=env.now,
                event_type="packet_arrival",
                packet=packet,
                node_id=current_node_id,
            ),
        )

        while env.now < context.sim_duration_s and packet.hops < MAX_FORWARD_HOPS:
            if context.routing_engine is None:
                self._drop(context, packet, current_node_id, "no_routing_engine")
                return
            try:
                next_hop = context.routing_engine.select_next_hop(
                    packet,
                    current_node_id,
                    context.graph,
                    registry,
                    context.combined_weight_overrides,
                )
            except Exception as exc:
                self._publish(
                    context,
                    EngineErrorEvent(
                        time=env.now,
                        event_type="engine_error",
                        component="routing",
                        error=str(exc),
                    ),
                )
                self._drop(context, packet, current_node_id, "routing_error")
                return

            self._publish(
                context,
                RoutingDecisionEvent(
                    time=env.now,
                    event_type="routing_decision",
                    packet=packet,
                    node_id=current_node_id,
                    next_hop=next_hop,
                    weight_overrides={
                        str(link_id): value
                        for link_id, value in context.combined_weight_overrides.items()
                    },
                ),
            )

            if (
                next_hop is None
                or next_hop == current_node_id
                or not context.graph.has_edge(current_node_id, next_hop)
            ):
                self._drop(context, packet, current_node_id, "no_route")
                return

            next_node = registry.get(next_hop)
            if (
                next_node is not None
                and next_node.node_type == "pod"
                and next_hop != packet.dst
            ):
                self._drop(context, packet, current_node_id, "pod_not_transit")
                return

            dequeue = getattr(current, "forward_packet", None)
            if dequeue is not None:
                dequeued = dequeue()
                if dequeued is None:
                    self._drop(context, packet, current_node_id, "queue_empty")
                    return

            self._publish(
                context,
                PacketTransmitEvent(
                    time=env.now,
                    event_type="packet_transmit",
                    packet=packet,
                    node_id=current_node_id,
                    to_node=next_hop,
                ),
            )

            link_id = LinkId(f"{current_node_id}->{next_hop}")
            link_resource = context.link_resources.get(link_id)
            if link_resource is None:
                link_resource = simpy.PriorityResource(env)
                context.link_resources[link_id] = link_resource

            edge_attrs = context.graph.edges[current_node_id, next_hop]
            capacity_gbps = float(edge_attrs.get("capacity", 100.0))
            capacity_fraction = float(
                edge_attrs.get("effective_capacity_fraction", 1.0)
            )

            request = link_resource.request(priority=packet.priority)
            yield request
            transmission_s = packet.size_bytes * 8.0 / (
                max(capacity_gbps, 1e-9) * max(capacity_fraction, 1e-9) * 1e9
            )
            yield env.timeout(transmission_s)
            link_resource.release(request)

            delay_s = (
                float(edge_attrs.get("propagation_delay_ms", 1.0)) / 1000.0
            )
            yield env.timeout(delay_s)

            if next_hop == packet.dst:
                self._deliver(context, packet, next_hop)
                return

            next_node = registry.get(next_hop)
            if next_node is None or not next_node.process_packet(packet):
                self._drop(context, packet, next_hop, "node_unavailable")
                return
            self._publish(
                context,
                PacketArrivalEvent(
                    time=env.now,
                    event_type="packet_arrival",
                    packet=packet,
                    node_id=next_hop,
                ),
            )
            packet.hops += 1
            packet.path_history.append(str(next_hop))
            current_node_id = next_hop
            current = next_node

        self._drop(context, packet, current_node_id, "max_hops")

    @staticmethod
    def _accept(context: SimulationContext, node: Node, packet: Packet) -> bool:
        """Accept `packet` at `node`; routes counters on the node."""
        return node.process_packet(packet)

    def _deliver(
        self,
        context: SimulationContext,
        packet: Packet,
        dst: NodeId,
    ) -> None:
        env = context.env
        dst_node = context.node_registry.get(dst)
        if dst_node is None or not dst_node.process_packet(packet):
            self._drop(context, packet, dst, "destination_unavailable")
            return
        self._publish(
            context,
            PacketDeliveredEvent(
                time=env.now,
                event_type="packet_delivered",
                packet=packet,
                node_id=dst,
                latency_s=max(0.0, env.now - packet.created_at),
            ),
        )
        if dst_node.node_type == "pod":
            store = context.compute_stores.get(dst)
            if store is not None:
                store.put(packet)

    def _drop(
        self, context: SimulationContext, packet: Packet, node_id: NodeId, reason: str
    ) -> None:
        node = context.node_registry.get(node_id)
        physics_induced = node is not None and not node.is_operational()
        if physics_induced:
            self._publish(
                context,
                PhysicsInducedDropEvent(
                    time=context.env.now,
                    event_type="packet_drop",
                    packet=packet,
                    node_id=node_id,
                    reason=reason,
                    cause="node_faulted",
                ),
            )
        else:
            self._publish(
                context,
                PacketDropEvent(
                    time=context.env.now,
                    event_type="packet_drop",
                    packet=packet,
                    node_id=node_id,
                    reason=reason,
                ),
            )

    def _publish(self, context: SimulationContext, event: SimulationEvent) -> None:
        context.event_bus.publish(event)
        if self._record_events:
            if (
                self._max_event_log_size is None
                or len(self._event_log) < self._max_event_log_size
            ):
                self._event_log.append(event)


OrbitDCSimulation = SkyNetraSimulation
