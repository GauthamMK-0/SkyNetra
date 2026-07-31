from __future__ import annotations

import dataclasses

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId, TimeSeconds
from skynetra.orchestration.events import (
    MetricsEvent,
    NodeEvent,
    PacketEvent,
    PhysicsEvent,
    SimulationEndEvent,
    SimulationEvent,
    SimulationStartEvent,
    TopologyEvent,
)


def test_simulation_event_defaults():
    ev = SimulationEvent(time=TimeSeconds(0.0), event_type="generic")
    assert ev.time == 0.0
    assert ev.event_type == "generic"


def test_simulation_start_event():
    ev = SimulationStartEvent(time=TimeSeconds(0.0), event_type="simulation_start")
    assert ev.config == {}

    ev_with_config = SimulationStartEvent(
        time=TimeSeconds(0.0), event_type="simulation_start", config={"key": "val"}
    )
    assert ev_with_config.config == {"key": "val"}


def test_simulation_end_event():
    ev = SimulationEndEvent(
        time=TimeSeconds(100.0), event_type="simulation_end", total_duration=100.0
    )
    assert ev.time == 100.0
    assert ev.total_duration == 100.0


def test_simulation_end_defaults():
    ev = SimulationEndEvent(time=TimeSeconds(0.0), event_type="simulation_end")
    assert ev.total_duration == 0.0


def test_node_event():
    ev = NodeEvent(
        time=TimeSeconds(5.0),
        event_type="node_update",
        node_id=NodeId("sat-1"),
        data={"temperature": 300.0},
    )
    assert ev.time == 5.0
    assert ev.node_id == "sat-1"
    assert ev.data == {"temperature": 300.0}


def test_node_event_defaults():
    ev = NodeEvent(time=TimeSeconds(0.0), event_type="node_update", node_id=NodeId("sat-1"))
    assert ev.data == {}


def test_packet_event():
    pkt = Packet(
        packet_id="pkt-1",
        source=NodeId("a"),
        destination=NodeId("b"),
        size_bytes=100,
        creation_time=TimeSeconds(0.0),
    )
    ev = PacketEvent(
        time=TimeSeconds(10.0), event_type="packet_generated", packet=pkt, status="generated"
    )
    assert ev.packet is pkt
    assert ev.status == "generated"


def test_packet_event_default_status():
    pkt = Packet(
        packet_id="pkt-1",
        source=NodeId("a"),
        destination=NodeId("b"),
        size_bytes=100,
        creation_time=TimeSeconds(0.0),
    )
    ev = PacketEvent(time=TimeSeconds(0.0), event_type="packet_generated", packet=pkt)
    assert ev.status == ""


def test_topology_event():
    ev = TopologyEvent(
        time=TimeSeconds(1.0), event_type="topology_update", edge_count=5, node_count=3
    )
    assert ev.edge_count == 5
    assert ev.node_count == 3


def test_topology_event_defaults():
    ev = TopologyEvent(time=TimeSeconds(0.0), event_type="topology_update")
    assert ev.edge_count == 0
    assert ev.node_count == 0


def test_physics_event():
    ev = PhysicsEvent(
        time=TimeSeconds(2.0),
        event_type="physics_update",
        node_id=NodeId("sat-1"),
        temperature=300.0,
        radiation_dose=0.5,
        power_available=1000.0,
    )
    assert ev.node_id == "sat-1"
    assert ev.temperature == 300.0
    assert ev.radiation_dose == 0.5
    assert ev.power_available == 1000.0


def test_physics_event_defaults():
    ev = PhysicsEvent(time=TimeSeconds(0.0), event_type="physics_update", node_id=NodeId("sat-1"))
    assert ev.temperature == 0.0
    assert ev.radiation_dose == 0.0
    assert ev.power_available == 0.0


def test_metrics_event():
    ev = MetricsEvent(
        time=TimeSeconds(3.0), event_type="metrics_collected", metrics={"cpu": 0.8, "mem": 0.5}
    )
    assert ev.metrics == {"cpu": 0.8, "mem": 0.5}


def test_metrics_event_defaults():
    ev = MetricsEvent(time=TimeSeconds(0.0), event_type="metrics_collected")
    assert ev.metrics == {}


def test_event_hierarchy():
    assert issubclass(SimulationStartEvent, SimulationEvent)
    assert issubclass(SimulationEndEvent, SimulationEvent)
    assert issubclass(NodeEvent, SimulationEvent)
    assert issubclass(PacketEvent, SimulationEvent)
    assert issubclass(TopologyEvent, SimulationEvent)
    assert issubclass(PhysicsEvent, SimulationEvent)
    assert issubclass(MetricsEvent, SimulationEvent)


def test_all_are_dataclasses():
    for cls in [
        SimulationEvent,
        SimulationStartEvent,
        SimulationEndEvent,
        NodeEvent,
        PacketEvent,
        TopologyEvent,
        PhysicsEvent,
        MetricsEvent,
    ]:
        assert dataclasses.is_dataclass(cls)
