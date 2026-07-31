"""
Orchestration layer (L3) — typed simulation events.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId, TimeSeconds


@dataclass
class SimulationEvent:
    time: TimeSeconds
    event_type: str


@dataclass
class SimulationStartEvent(SimulationEvent):
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationEndEvent(SimulationEvent):
    total_duration: float = 0.0


@dataclass
class NodeEvent(SimulationEvent):
    node_id: NodeId
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PacketEvent(SimulationEvent):
    packet: Packet
    status: str = ""


@dataclass
class TopologyEvent(SimulationEvent):
    edge_count: int = 0
    node_count: int = 0


@dataclass
class PhysicsEvent(SimulationEvent):
    node_id: NodeId
    temperature: float = 0.0
    radiation_dose: float = 0.0
    power_available: float = 0.0


@dataclass
class MetricsEvent(SimulationEvent):
    metrics: Dict[str, float] = field(default_factory=dict)
