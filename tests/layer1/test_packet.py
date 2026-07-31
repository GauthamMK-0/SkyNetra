from __future__ import annotations

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId, TimeSeconds


def test_packet_creation():
    pkt = Packet(
        packet_id="pkt-001",
        source=NodeId("relay-a"),
        destination=NodeId("gs-1"),
        size_bytes=1500,
        creation_time=TimeSeconds(0.0),
    )
    assert pkt.packet_id == "pkt-001"
    assert pkt.source == "relay-a"
    assert pkt.destination == "gs-1"
    assert pkt.size_bytes == 1500
    assert pkt.creation_time == 0.0


def test_packet_defaults():
    pkt = Packet(
        packet_id="pkt-002",
        source=NodeId("sat-1"),
        destination=NodeId("sat-2"),
        size_bytes=512,
        creation_time=TimeSeconds(10.0),
    )
    assert pkt.payload is None
    assert pkt.ttl == 64
    assert pkt.priority == 0
    assert pkt.path == []
    assert pkt.hops == 0
    assert pkt.arrived is False


def test_packet_custom_fields():
    pkt = Packet(
        packet_id="pkt-003",
        source=NodeId("pod-1"),
        destination=NodeId("relay-b"),
        size_bytes=4096,
        creation_time=TimeSeconds(5.0),
        payload={"model": "resnet18"},
        ttl=32,
        priority=1,
        path=[NodeId("pod-1"), NodeId("relay-a"), NodeId("relay-b")],
        hops=2,
        arrived=True,
    )
    assert pkt.payload == {"model": "resnet18"}
    assert pkt.ttl == 32
    assert pkt.priority == 1
    assert len(pkt.path) == 3
    assert pkt.hops == 2
    assert pkt.arrived is True


def test_packet_is_dataclass():
    import dataclasses
    assert dataclasses.is_dataclass(Packet)


def test_packet_equality():
    pkt1 = Packet(
        packet_id="pkt-001",
        source=NodeId("a"),
        destination=NodeId("b"),
        size_bytes=100,
        creation_time=TimeSeconds(0.0),
    )
    pkt2 = Packet(
        packet_id="pkt-001",
        source=NodeId("a"),
        destination=NodeId("b"),
        size_bytes=100,
        creation_time=TimeSeconds(0.0),
    )
    assert pkt1 == pkt2


def test_packet_inequality():
    pkt1 = Packet(
        packet_id="pkt-001",
        source=NodeId("a"),
        destination=NodeId("b"),
        size_bytes=100,
        creation_time=TimeSeconds(0.0),
    )
    pkt2 = Packet(
        packet_id="pkt-002",
        source=NodeId("a"),
        destination=NodeId("b"),
        size_bytes=100,
        creation_time=TimeSeconds(0.0),
    )
    assert pkt1 != pkt2
