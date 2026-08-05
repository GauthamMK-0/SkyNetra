"""
Orchestration layer (L3) — typed simulation events.

Every event is a plain dataclass carrying `time` (seconds, taken from
`env.now` at publish time) and `event_type`. The L3 engine publishes
these on the L0 `EventBus`, whose dispatch is inheritance-aware: a
subscriber registered on `PacketDropEvent` also receives
`PhysicsInducedDropEvent` instances.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId


@dataclass
class SimulationEvent:
    """Base class for every L3 simulation event."""

    time: float
    event_type: str


@dataclass
class TopologyUpdateEvent(SimulationEvent):
    """Published when the topology graph is rebuilt/refreshed."""

    topology_version: int = 0
    edge_count: int = 0
    node_count: int = 0


@dataclass
class PacketEvent(SimulationEvent):
    """Base class for packet lifecycle events."""

    packet: Packet
    node_id: NodeId


@dataclass
class PacketArrivalEvent(PacketEvent):
    """Published when a packet is accepted at a node."""

    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class PacketTransmitEvent(PacketEvent):
    """Published when a packet is transmitted from a node."""

    to_node: NodeId | None = None


@dataclass
class PacketDropEvent(PacketEvent):
    """Published when a packet is dropped (no route, full queue, ...)."""

    reason: str = ""


@dataclass
class PhysicsInducedDropEvent(PacketDropEvent):
    """A drop caused by a physics-induced fault (inherits PacketDropEvent)."""

    cause: str = "physics"


@dataclass
class PacketDeliveredEvent(PacketEvent):
    """Published when a packet reaches its destination node."""

    latency_s: float = 0.0


@dataclass
class ComputeJobCompleteEvent(SimulationEvent):
    """Published when a compute job finishes at a pod."""

    node_id: NodeId
    packet: Packet


@dataclass
class PhysicsTickEvent(SimulationEvent):
    """Published after each physics tick; carries per-node state.

    `node_state` maps node id -> {"physics_state": {...},
    "metrics_state": {...}}; `active_models` lists the enabled physics
    model names that produced the tick.
    """

    tick: int = 0
    node_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_models: list[str] = field(default_factory=list)


@dataclass
class RoutingDecisionEvent(PacketEvent):
    """Published for every routing decision made during forwarding."""

    next_hop: NodeId | None = None
    weight_overrides: dict[str, float] = field(default_factory=dict)


@dataclass
class EngineErrorEvent(SimulationEvent):
    """Published when a Layer 2 component raises; the engine continues."""

    component: str = ""
    error: str = ""
