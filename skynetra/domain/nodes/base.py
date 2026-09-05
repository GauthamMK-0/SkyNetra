"""
Domain layer (L1) — node base model.

A Layer 1 domain node is pure data plus minimal behavior: queueing,
packet acceptance, and state snapshot. NO routing or physics ALGORITHMS
live here — those are injected as plain values/dicts by Layer 2/3, never
imported as classes.

State is carried in two plain dicts whose shapes are owned by Layer 1:

  physics_state:
      temperature_k           (K, default 293.15)
      radiation_dose_rad      (cumulative dose, rad, default 0.0)
      power_available_w       (W, default 1000.0)
      fault_probability       (unitless [0, 1], default 0.0)
  metrics_state:
      packets_sent            (int)
      packets_received        (int)
      packets_dropped         (int)
      compute_tasks           (int)
      compute_flops           (float)
      energy_consumed         (float)

Layer 2 physics engines push numbers into a node via `update_physics`
and never mutate the dicts directly; the node re-derives its operational
state (fault detection) on every update. `snapshot()` returns a plain
copy-safe dict so Layer 3 metrics collectors can read state without
touching internals.

The node accepts a `skynetra.foundation.eventbus.EventBus` via
constructor injection (never a global registry). It publishes
L1-owned `NodeEvent` records on packet acceptance/drop; Layer 3 maps
those to its own typed simulation events.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId

DEFAULT_PHYSICS_STATE: dict[str, float] = {
    "temperature_k": 293.15,
    "radiation_dose_rad": 0.0,
    "power_available_w": 1000.0,
    "fault_probability": 0.0,
}

DEFAULT_METRICS_STATE: dict[str, Any] = {
    "packets_sent": 0,
    "packets_received": 0,
    "packets_dropped": 0,
    "compute_tasks": 0,
    "compute_flops": 0.0,
    "energy_consumed": 0.0,
}

TEMP_NOMINAL_K = 300.0
TEMP_DEGRADATION_SIGMA_K = 50.0
TEMP_FAULT_THRESHOLD_K = 400.0
RADIATION_REFERENCE_DOSE_RAD = 1000.0
FAULT_PROBABILITY_THRESHOLD = 0.5


@dataclass
class NodeEvent:
    """Minimal L1-owned node lifecycle event published on the EventBus.

    Layer 3 wraps this into its own typed simulation events; Layer 1
    only records facts.
    """

    node_id: NodeId
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


class Node(ABC):
    """Layer 1 domain node. Pure data + minimal behavior:
    queueing, packet acceptance, state snapshot. NO routing or physics
    ALGORITHMS live here — those are injected as plain values/dicts by
    Layer 2/3, never imported as classes.
    """

    def __init__(
        self, node_id: NodeId, node_type: str, event_bus: EventBus | None = None
    ) -> None:
        self._node_id = node_id
        self._node_type = node_type
        self._event_bus = event_bus if event_bus is not None else EventBus()
        self._physics_state: dict[str, float] = dict(DEFAULT_PHYSICS_STATE)
        self._metrics_state: dict[str, Any] = dict(DEFAULT_METRICS_STATE)
        self._fault_active = False

    @property
    def node_id(self) -> NodeId:
        return self._node_id

    @property
    def node_type(self) -> str:
        return self._node_type

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def physics_state(self) -> dict[str, float]:
        """Live physics state dict (Layer 2 engines write via update_physics)."""
        return self._physics_state

    @property
    def metrics_state(self) -> dict[str, Any]:
        """Live metrics state dict."""
        return self._metrics_state

    def update_physics(self, delta: dict[str, Any]) -> None:
        """Merge `delta` (computed by a Layer 2 physics engine) into the
        physics state and re-derive fault/operational status.
        """
        self._physics_state.update(delta)
        self._fault_active = self._evaluate_fault()

    def is_operational(self) -> bool:
        """True while the node has not been driven into a fault state."""
        return not self._fault_active

    def thermal_degradation_factor(self) -> float:
        """Fraction of nominal performance retained at the current
        temperature: 1.0 at the nominal temperature, decaying
        exponentially above it. Deterministic; Layer 2 physics engines
        may override with their own models via update_physics.
        """
        excess_k = max(0.0, self._physics_state["temperature_k"] - TEMP_NOMINAL_K)
        return math.exp(-excess_k / TEMP_DEGRADATION_SIGMA_K)

    def radiation_degradation_factor(self) -> float:
        """Fraction of nominal performance retained at the current
        cumulative radiation dose: 1.0 at zero dose, 0.5 at the
        reference dose.
        """
        dose = self._physics_state["radiation_dose_rad"]
        return 1.0 / (1.0 + dose / RADIATION_REFERENCE_DOSE_RAD)

    def snapshot(self) -> dict[str, Any]:
        """Plain copy-safe state snapshot for Layer 3 metrics readers."""
        return {
            "node_id": self._node_id,
            "node_type": self._node_type,
            "operational": self.is_operational(),
            "physics_state": dict(self._physics_state),
            "metrics_state": dict(self._metrics_state),
        }

    def _evaluate_fault(self) -> bool:
        return (
            self._physics_state["fault_probability"] >= FAULT_PROBABILITY_THRESHOLD
            or self._physics_state["temperature_k"] >= TEMP_FAULT_THRESHOLD_K
        )

    def _begin_packet_processing(self, packet: Packet) -> bool:
        """Common acceptance guard: a faulted node drops every packet."""
        if not self.is_operational():
            self._metrics_state["packets_dropped"] += 1
            self._publish("packet_dropped", {"packet_id": packet.packet_id})
            return False
        return True

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self._event_bus.has_subscribers(NodeEvent):
            self._event_bus.publish(
                NodeEvent(node_id=self._node_id, event_type=event_type, payload=payload)
            )

    @abstractmethod
    def process_packet(self, packet: Packet) -> bool:
        """Accept a packet for handling; returns False if rejected/dropped."""
        ...

    @abstractmethod
    def get_queue_depth(self) -> int:
        """Number of packets currently buffered at this node."""
        ...

    @abstractmethod
    def get_utilization(self) -> float:
        """Instantaneous utilization in [0.0, 1.0]."""
        ...
