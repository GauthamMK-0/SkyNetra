from __future__ import annotations

import pytest
import simpy

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId
from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.events import (
    PacketDeliveredEvent,
    PacketDropEvent,
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


def _context(nodes: dict[NodeId, Node]) -> SimulationContext:
    return SimulationContext(env=simpy.Environment(), node_registry=nodes)


class TestNetworkMetricsCollector:
    def test_name(self):
        assert NetworkMetricsCollector().name() == "network"

    def test_counts_node_metrics_state(self):
        node = RelayNode(NodeId("sat-1"))
        node.process_packet(_packet("p1"))
        node.forward_packet()
        node.forward_packet()
        context = _context({NodeId("sat-1"): node})

        metrics = NetworkMetricsCollector().collect(context)
        assert (
            metrics["total_packets"]
            == node.metrics_state["packets_sent"] + node.metrics_state["packets_received"]
        )

    def test_tallies_delivered_and_dropped_via_events(self):
        bus = EventBus()
        collector = NetworkMetricsCollector()
        collector.attach(bus)

        bus.publish(
            PacketDeliveredEvent(
                time=1.0,
                event_type="packet_delivered",
                packet=_packet("p1"),
                node_id=NodeId("gs-1"),
                latency_s=0.5,
            )
        )
        bus.publish(
            PacketDeliveredEvent(
                time=2.0,
                event_type="packet_delivered",
                packet=_packet("p2"),
                node_id=NodeId("gs-1"),
                latency_s=0.25,
            )
        )
        bus.publish(
            PacketDropEvent(
                time=3.0,
                event_type="packet_drop",
                packet=_packet("p3"),
                node_id=NodeId("sat-1"),
                reason="no_route",
            )
        )
        metrics = collector.collect(_context({}))
        assert metrics["delivered"] == 2
        assert metrics["dropped"] == 1
        assert metrics["avg_latency_s"] == pytest.approx(0.375)

    def test_physics_induced_drop_counts_as_drop(self):
        bus = EventBus()
        collector = NetworkMetricsCollector()
        collector.attach(bus)

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
        metrics = collector.collect(_context({}))
        assert metrics["delivered"] == 0
        assert metrics["dropped"] == 1

    def test_avg_latency_zero_without_deliveries(self):
        metrics = NetworkMetricsCollector().collect(_context({}))
        assert metrics["avg_latency_s"] == 0.0
