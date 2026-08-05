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
from skynetra.orchestration.metrics.aggregator import MetricsAggregator
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.physics_metrics import PhysicsMetricsCollector
from skynetra.orchestration.metrics.registry import (
    STRATEGIES,
    build_metrics_collectors,
)
from skynetra.orchestration.metrics.topology_metrics import TopologyMetricsCollector
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
    "NetworkMetricsCollector",
    "ComputeMetricsCollector",
    "TopologyMetricsCollector",
    "PhysicsMetricsCollector",
    "MetricsAggregator",
    "STRATEGIES",
    "build_metrics_collectors",
]
