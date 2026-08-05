from __future__ import annotations

from skynetra.domain.nodes.base import FAULT_PROBABILITY_THRESHOLD
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId
from skynetra.orchestration.events import (
    PacketDropEvent,
    PhysicsInducedDropEvent,
    PhysicsTickEvent,
)
from skynetra.orchestration.metrics.physics_metrics import (
    THERMAL_THROTTLE_THRESHOLD_K,
    PhysicsMetricsCollector,
)


def _packet(packet_id: str) -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("a"),
        dst=NodeId("b"),
        size_bytes=100,
        packet_type="data",
        created_at=0.0,
    )


def _node_state(
    temperature_k: float,
    fault_probability: float = 0.0,
    energy: float = 0.0,
) -> dict[str, dict[str, float]]:
    return {
        "physics_state": {
            "temperature_k": temperature_k,
            "radiation_dose_rad": 0.0,
            "power_available_w": 1000.0,
            "fault_probability": fault_probability,
        },
        "metrics_state": {"energy_consumed": energy},
    }


def _tick(
    node_state: dict[str, dict[str, float]],
    tick: int = 1,
    active_models: list[str] | None = None,
) -> PhysicsTickEvent:
    return PhysicsTickEvent(
        time=float(tick),
        event_type="physics_tick",
        tick=tick,
        node_state=node_state,
        active_models=active_models or [],
    )


def _attach(bus: EventBus) -> PhysicsMetricsCollector:
    collector = PhysicsMetricsCollector()
    collector.attach(bus)
    return collector


class TestPhysicsMetricsCollector:
    def test_name(self):
        assert PhysicsMetricsCollector().name == "physics_metrics"

    def test_starts_at_zero(self):
        summary = _attach(EventBus()).get_summary()
        assert summary["thermal_throttle_events"] == 0
        assert summary["radiation_fault_events"] == 0
        assert summary["physics_caused_drops"] == 0
        assert summary["avg_temperature"] == 0.0
        assert summary["total_energy_consumed"] == 0.0
        assert summary["active_models"] == []

    def test_counts_thermal_throttling_from_ticks(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(_tick({"sat-1": _node_state(THERMAL_THROTTLE_THRESHOLD_K + 10.0)}))
        bus.publish(_tick({"sat-1": _node_state(293.15)}))

        summary = collector.get_summary()
        assert summary["thermal_throttle_events"] == 1
        assert summary["radiation_fault_events"] == 0

    def test_throttling_excludes_thermal_faults(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(_tick({"sat-1": _node_state(500.0)}))
        assert collector.get_summary()["thermal_throttle_events"] == 0

    def test_counts_radiation_faults(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            _tick(
                {"sat-1": _node_state(300.0, fault_probability=FAULT_PROBABILITY_THRESHOLD + 0.1)}
            )
        )
        summary = collector.get_summary()
        assert summary["radiation_fault_events"] == 1
        assert summary["thermal_throttle_events"] == 0

    def test_counts_physics_induced_drops_only(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            PhysicsInducedDropEvent(
                time=1.0,
                event_type="packet_drop",
                packet=_packet("p1"),
                node_id=NodeId("sat-1"),
                reason="node_faulted",
                cause="node_faulted",
            )
        )
        bus.publish(
            PacketDropEvent(
                time=2.0,
                event_type="packet_drop",
                packet=_packet("p2"),
                node_id=NodeId("sat-1"),
                reason="no_route",
            )
        )
        summary = collector.get_summary()
        assert summary["physics_caused_drops"] == 1

    def test_averages_temperature_and_sums_energy(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            _tick(
                {"sat-1": _node_state(300.0, energy=10.0), "sat-2": _node_state(400.0, energy=20.0)}
            )
        )
        bus.publish(_tick({"sat-1": _node_state(300.0, energy=15.0)}))

        summary = collector.get_summary()
        assert summary["avg_temperature"] == (300.0 + 400.0 + 300.0) / 3
        assert summary["total_energy_consumed"] == 15.0 + 20.0

    def test_active_models_from_latest_tick(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(_tick({"sat-1": _node_state(293.15)}, active_models=["ThermalModel"]))
        bus.publish(
            _tick(
                {"sat-1": _node_state(293.15)},
                active_models=["ThermalModel", "RadiationModel"],
            )
        )
        assert set(collector.get_summary()["active_models"]) == {
            "ThermalModel",
            "RadiationModel",
        }

    def test_reset_clears_tallies(self):
        bus = EventBus()
        collector = _attach(bus)
        bus.publish(_tick({"sat-1": _node_state(THERMAL_THROTTLE_THRESHOLD_K + 5.0)}))

        collector.reset()
        summary = collector.get_summary()
        assert summary["thermal_throttle_events"] == 0
        assert summary["avg_temperature"] == 0.0
        assert summary["active_models"] == []

    def test_to_dataframe(self):
        import pandas as pd

        df = PhysicsMetricsCollector().to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == [
            "thermal_throttle_events",
            "radiation_fault_events",
            "physics_caused_drops",
            "avg_temperature",
            "total_energy_consumed",
            "active_models",
        ]
        assert len(df) == 1
