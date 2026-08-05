from __future__ import annotations

import dataclasses

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId
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


def _packet(packet_id: str = "pkt-1") -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("a"),
        dst=NodeId("b"),
        size_bytes=100,
        packet_type="data",
        created_at=0.0,
    )


class TestEventDefaults:
    def test_base_event(self):
        ev = SimulationEvent(time=1.0, event_type="generic")
        assert ev.time == 1.0
        assert ev.event_type == "generic"

    def test_topology_update_event(self):
        ev = TopologyUpdateEvent(time=1.0, event_type="topology_update")
        assert ev.topology_version == 0
        assert ev.edge_count == 0
        assert ev.node_count == 0

    def test_packet_arrival_event(self):
        ev = PacketArrivalEvent(
            time=1.0, event_type="packet_arrival", packet=_packet(), node_id=NodeId("sat-1")
        )
        assert ev.packet is not None
        assert ev.node_id == "sat-1"
        assert ev.payload == {}

    def test_packet_transmit_event(self):
        ev = PacketTransmitEvent(
            time=1.0, event_type="packet_transmit", packet=_packet(), node_id=NodeId("sat-1")
        )
        assert ev.to_node is None

    def test_packet_drop_event(self):
        ev = PacketDropEvent(
            time=1.0, event_type="packet_drop", packet=_packet(), node_id=NodeId("sat-1")
        )
        assert ev.reason == ""

    def test_packet_delivered_event(self):
        ev = PacketDeliveredEvent(
            time=2.0, event_type="packet_delivered", packet=_packet(), node_id=NodeId("gs-1")
        )
        assert ev.latency_s == 0.0

    def test_compute_job_complete_event(self):
        ev = ComputeJobCompleteEvent(
            time=3.0, event_type="compute_job_complete", node_id=NodeId("pod-1"), packet=_packet()
        )
        assert ev.node_id == "pod-1"

    def test_physics_tick_event(self):
        ev = PhysicsTickEvent(time=4.0, event_type="physics_tick")
        assert ev.tick == 0
        assert ev.node_state == {}

    def test_routing_decision_event(self):
        ev = RoutingDecisionEvent(
            time=5.0, event_type="routing_decision", packet=_packet(), node_id=NodeId("sat-1")
        )
        assert ev.next_hop is None
        assert ev.weight_overrides == {}

    def test_engine_error_event(self):
        ev = EngineErrorEvent(time=6.0, event_type="engine_error")
        assert ev.component == ""
        assert ev.error == ""

    def test_physics_induced_drop_event(self):
        ev = PhysicsInducedDropEvent(
            time=7.0, event_type="packet_drop", packet=_packet(), node_id=NodeId("sat-1")
        )
        assert ev.reason == ""
        assert ev.cause == "physics"


class TestEventHierarchy:
    def test_all_subclass_simulation_event(self):
        for cls in [
            TopologyUpdateEvent,
            PacketArrivalEvent,
            PacketTransmitEvent,
            PacketDropEvent,
            PacketDeliveredEvent,
            ComputeJobCompleteEvent,
            PhysicsTickEvent,
            RoutingDecisionEvent,
            PhysicsInducedDropEvent,
            EngineErrorEvent,
        ]:
            assert issubclass(cls, SimulationEvent)

    def test_packet_events_share_packet_fields(self):
        for cls in [
            PacketArrivalEvent,
            PacketTransmitEvent,
            PacketDropEvent,
            PacketDeliveredEvent,
            RoutingDecisionEvent,
        ]:
            assert "packet" in cls.__dataclass_fields__
            assert "node_id" in cls.__dataclass_fields__

    def test_physics_induced_drop_is_packet_drop(self):
        assert issubclass(PhysicsInducedDropEvent, PacketDropEvent)

    def test_all_are_dataclasses(self):
        for cls in [
            SimulationEvent,
            TopologyUpdateEvent,
            PacketArrivalEvent,
            PacketTransmitEvent,
            PacketDropEvent,
            PacketDeliveredEvent,
            ComputeJobCompleteEvent,
            PhysicsTickEvent,
            RoutingDecisionEvent,
            PhysicsInducedDropEvent,
            EngineErrorEvent,
        ]:
            assert dataclasses.is_dataclass(cls)


class TestInheritanceAwareDispatch:
    def test_physics_induced_drop_reaches_packet_drop_subscribers(self):
        bus = EventBus()
        seen: list[PacketDropEvent] = []

        bus.subscribe(PacketDropEvent, lambda ev: seen.append(ev))
        bus.publish(
            PhysicsInducedDropEvent(
                time=1.0,
                event_type="packet_drop",
                packet=_packet(),
                node_id=NodeId("sat-1"),
                reason="node_faulted",
                cause="node_faulted",
            )
        )

        assert len(seen) == 1
        assert isinstance(seen[0], PhysicsInducedDropEvent)
        assert seen[0].reason == "node_faulted"

    def test_base_event_subscribers_receive_typed_events(self):
        bus = EventBus()
        seen: list[SimulationEvent] = []

        bus.subscribe(SimulationEvent, lambda ev: seen.append(ev))
        bus.publish(
            TopologyUpdateEvent(
                time=1.0,
                event_type="topology_update",
                topology_version=2,
                edge_count=4,
                node_count=3,
            )
        )
        bus.publish(
            EngineErrorEvent(time=2.0, event_type="engine_error", component="routing", error="boom")
        )

        assert len(seen) == 2
        assert [ev.event_type for ev in seen] == ["topology_update", "engine_error"]

    def test_unsubscribe_stops_delivery(self):
        bus = EventBus()
        seen: list[PacketDropEvent] = []

        def handler(ev: PacketDropEvent) -> None:
            seen.append(ev)

        bus.subscribe(PacketDropEvent, handler)
        bus.unsubscribe(PacketDropEvent, handler)
        bus.publish(
            PacketDropEvent(
                time=1.0, event_type="packet_drop", packet=_packet(), node_id=NodeId("a")
            )
        )
        assert seen == []
