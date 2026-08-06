"""
Orchestration layer (L3) — simulation context.

The context is the single live data structure owned by the L3 core: it
carries the SimPy environment, the event bus, the node registry, the
current topology graph, the Layer 2 engines (routing, physics), the
metrics aggregator, and the simulation configuration. The engine's
processes read and mutate it every tick; metrics collectors read it at
snapshot time.

`scratchpad` is a free-form dict for cross-component bookkeeping (the
engine records topology versions, metrics snapshots, and event counters
there); `combined_weight_overrides` holds the per-link routing weights
computed by the enabled physics models on the most recent physics tick.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import networkx as nx
import simpy

from skynetra.domain.nodes.base import Node
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import PropagatorInterface
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import LinkId, NodeId

if TYPE_CHECKING:
    from skynetra.orchestration.metrics.aggregator import MetricsAggregator


@dataclass
class SimulationContext:
    """Live state shared by the L3 simulation processes."""

    env: simpy.Environment
    event_bus: EventBus = field(default_factory=EventBus)
    node_registry: dict[NodeId, Node] = field(default_factory=dict)
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    routing_engine: RoutingEngine | None = None
    physics_orchestrator: PhysicsOrchestrator | None = None
    metrics_aggregator: MetricsAggregator | None = None
    sim_duration_s: float = 60.0
    topology_update_interval_s: float = 10.0
    physics_tick_interval_s: float = 1.0
    seed: int = 42
    constellation: ConstellationConfig | None = None
    propagator: PropagatorInterface | None = None
    pod_ids: list[NodeId] = field(default_factory=list)
    ground_station_ids: list[NodeId] = field(default_factory=list)
    current_time_s: float = 0.0
    topology_version: int = 0
    combined_weight_overrides: dict[LinkId, float] = field(default_factory=dict)
    link_resources: dict[LinkId, simpy.PriorityResource] = field(default_factory=dict)
    compute_stores: dict[NodeId, simpy.Store] = field(default_factory=dict)
    debug_routing: bool = False
    scratchpad: dict[str, Any] = field(default_factory=dict)
