"""
Orchestration layer (L3) — SimPy simulation core, events, metrics.

May import from: itself, engines (L2), domain (L1), foundation (L0).
"""

from __future__ import annotations

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.engine import OrbitDCSimulation
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
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import (
    get_metrics_collector,
    list_metrics_collectors,
)
from skynetra.orchestration.results import SimulationResults

__all__ = [
    "OrbitDCSimulation",
    "SimulationContext",
    "SimulationResults",
    "SimulationEvent",
    "TopologyUpdateEvent",
    "PacketArrivalEvent",
    "PacketTransmitEvent",
    "PacketDropEvent",
    "PacketDeliveredEvent",
    "ComputeJobCompleteEvent",
    "PhysicsTickEvent",
    "RoutingDecisionEvent",
    "PhysicsInducedDropEvent",
    "EngineErrorEvent",
    "MetricsCollector",
    "get_metrics_collector",
    "list_metrics_collectors",
]
