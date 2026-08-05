from __future__ import annotations

import pytest

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId
from skynetra.orchestration.events import (
    PacketDeliveredEvent,
    PacketDropEvent,
    PacketTransmitEvent,
    PhysicsInducedDropEvent,
)
from skynetra.orchestration.metrics.network import NetworkMetricsCollector


def _packet(packet_id: str) -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("a"),
        dst=NodeId("b"),
        size_bytes=100,
        packet_type="data",
        created_at=0.0,
    )


def _attach(bus: EventBus) -> NetworkMetricsCollector:
    collector = NetworkMetricsCollector()
    collector.attach(bus)
    return collector


class TestNetworkMetricsCollector:
    def test_name(self):
        assert NetworkMetricsCollector().name == "network_metrics"

    def test_starts_at_zero(self):
        summary = _attach(EventBus()).get_summary()
        assert summary["delivered"] == 0
        assert summary["dropped"] == 0
        assert summary["transmitted"] == 0
        assert summary["avg_latency_s"] == 0.0
        assert summary["drop_rate"] == 0.0

    def test_accumulates_delivered_dropped_transmitted(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            PacketTransmitEvent(
                time=1.0,
                event_type="packet_transmit",
                packet=_packet("p1"),
                node_id=NodeId("a"),
                to_node=NodeId("b"),
            )
        )
        bus.publish(
            PacketTransmitEvent(
                time=2.0,
                event_type="packet_transmit",
                packet=_packet("p2"),
                node_id=NodeId("a"),
                to_node=NodeId("b"),
            )
        )
        bus.publish(
            PacketDeliveredEvent(
                time=3.0,
                event_type="packet_delivered",
                packet=_packet("p1"),
                node_id=NodeId("b"),
                latency_s=0.5,
            )
        )
        bus.publish(
            PacketDropEvent(
                time=4.0,
                event_type="packet_drop",
                packet=_packet("p2"),
                node_id=NodeId("a"),
                reason="no_route",
            )
        )

        summary = collector.get_summary()
        assert summary["delivered"] == 1
        assert summary["dropped"] == 1
        assert summary["transmitted"] == 2
        assert summary["avg_latency_s"] == 0.5
        assert summary["drop_rate"] == 0.5

    def test_average_latency_over_multiple_deliveries(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            PacketDeliveredEvent(
                time=1.0,
                event_type="packet_delivered",
                packet=_packet("p1"),
                node_id=NodeId("b"),
                latency_s=0.2,
            )
        )
        bus.publish(
            PacketDeliveredEvent(
                time=2.0,
                event_type="packet_delivered",
                packet=_packet("p2"),
                node_id=NodeId("b"),
                latency_s=0.4,
            )
        )

        summary = collector.get_summary()
        assert summary["delivered"] == 2
        assert summary["avg_latency_s"] == pytest.approx(0.3)

    def test_physics_induced_drop_counts_as_drop(self):
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
        assert collector.get_summary()["dropped"] == 1

    def test_reset_clears_tallies(self):
        bus = EventBus()
        collector = _attach(bus)
        bus.publish(
            PacketDeliveredEvent(
                time=1.0,
                event_type="packet_delivered",
                packet=_packet("p1"),
                node_id=NodeId("b"),
                latency_s=0.5,
            )
        )
        bus.publish(
            PacketDropEvent(
                time=2.0,
                event_type="packet_drop",
                packet=_packet("p2"),
                node_id=NodeId("a"),
                reason="no_route",
            )
        )

        collector.reset()
        summary = collector.get_summary()
        assert summary["delivered"] == 0
        assert summary["dropped"] == 0
        assert summary["transmitted"] == 0

    def test_to_dataframe(self):
        import pandas as pd

        df = NetworkMetricsCollector().to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == [
            "delivered",
            "dropped",
            "transmitted",
            "avg_latency_s",
            "drop_rate",
        ]
        assert len(df) == 1
