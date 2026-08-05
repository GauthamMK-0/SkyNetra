from __future__ import annotations

import simpy

from skynetra.domain.nodes.base import FAULT_PROBABILITY_THRESHOLD
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.physics.orchestrator import PhysicsOrchestrator
from skynetra.engines.physics.registry import build_physics_models
from skynetra.foundation.types import NodeId
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.physics_metrics import (
    THERMAL_THROTTLE_THRESHOLD_K,
    PhysicsMetricsCollector,
)


def _context(
    nodes: dict[NodeId, object],
    physics: PhysicsOrchestrator | None = None,
) -> SimulationContext:
    return SimulationContext(
        env=simpy.Environment(),
        node_registry=nodes,  # type: ignore[arg-type]
        physics_orchestrator=physics,
    )


class TestPhysicsMetricsCollector:
    def test_name(self):
        assert PhysicsMetricsCollector().name() == "physics"

    def test_defaults_with_clean_registry(self):
        node = RelayNode(NodeId("sat-1"))
        metrics = PhysicsMetricsCollector().collect(_context({NodeId("sat-1"): node}))
        assert metrics["thermal_throttle_events"] == 0
        assert metrics["radiation_fault_events"] == 0
        assert metrics["total_energy_consumed"] == 0.0
        assert metrics["num_nodes"] == 1
        assert metrics["active_models"] == []

    def test_counts_thermal_throttling(self):
        node = RelayNode(NodeId("sat-1"))
        node.update_physics({"temperature_k": THERMAL_THROTTLE_THRESHOLD_K + 10.0})
        metrics = PhysicsMetricsCollector().collect(_context({NodeId("sat-1"): node}))
        assert metrics["thermal_throttle_events"] == 1
        assert metrics["radiation_fault_events"] == 0
        assert metrics["avg_temperature"] == THERMAL_THROTTLE_THRESHOLD_K + 10.0

    def test_throttling_excludes_thermal_faults(self):
        node = RelayNode(NodeId("sat-1"))
        node.update_physics({"temperature_k": 500.0})
        metrics = PhysicsMetricsCollector().collect(_context({NodeId("sat-1"): node}))
        assert metrics["thermal_throttle_events"] == 0

    def test_counts_radiation_faults(self):
        node = RelayNode(NodeId("sat-1"))
        node.update_physics({"fault_probability": FAULT_PROBABILITY_THRESHOLD + 0.1})
        metrics = PhysicsMetricsCollector().collect(_context({NodeId("sat-1"): node}))
        assert metrics["radiation_fault_events"] == 1
        assert metrics["thermal_throttle_events"] == 0

    def test_reports_active_physics_models(self):
        physics = PhysicsOrchestrator(
            build_physics_models(
                [
                    {"name": "thermal", "config": {"enabled": True}},
                    {"name": "radiation", "config": {"enabled": True}},
                ]
            )
        )
        node = RelayNode(NodeId("sat-1"))
        metrics = PhysicsMetricsCollector().collect(
            _context({NodeId("sat-1"): node}, physics=physics)
        )
        assert set(metrics["active_models"]) == {"ThermalModel", "RadiationModel"}

    def test_summed_energy_and_average_temperature(self):
        node_a = RelayNode(NodeId("sat-1"))
        node_a.update_physics({"temperature_k": 300.0})
        node_b = RelayNode(NodeId("sat-2"))
        node_b.update_physics({"temperature_k": 400.0})
        metrics = PhysicsMetricsCollector().collect(
            _context({NodeId("sat-1"): node_a, NodeId("sat-2"): node_b})
        )
        assert metrics["avg_temperature"] == 350.0
        assert metrics["num_nodes"] == 2
        assert metrics["active_models"] == []
