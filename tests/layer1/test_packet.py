from __future__ import annotations

import dataclasses

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId


def test_packet_creation():
    pkt = Packet(
        packet_id="pkt-001",
        src=NodeId("relay-a"),
        dst=NodeId("gs-1"),
        size_bytes=1500,
        packet_type="data",
        created_at=0.0,
    )
    assert pkt.packet_id == "pkt-001"
    assert pkt.src == "relay-a"
    assert pkt.dst == "gs-1"
    assert pkt.size_bytes == 1500
    assert pkt.packet_type == "data"
    assert pkt.created_at == 0.0


def test_packet_defaults():
    pkt = Packet(
        packet_id="pkt-002",
        src=NodeId("sat-1"),
        dst=NodeId("sat-2"),
        size_bytes=512,
        packet_type="telemetry",
        created_at=10.0,
    )
    assert pkt.flops_required == 0.0
    assert pkt.priority == 0
    assert pkt.hops == 0
    assert pkt.path_history == []
    assert pkt.metadata == {}


def test_packet_custom_fields():
    pkt = Packet(
        packet_id="pkt-003",
        src=NodeId("pod-1"),
        dst=NodeId("relay-b"),
        size_bytes=4096,
        packet_type="compute",
        created_at=5.0,
        flops_required=1e12,
        priority=1,
        hops=2,
        path_history=["pod-1", "relay-a", "relay-b"],
        metadata={"model": "resnet18"},
    )
    assert pkt.flops_required == 1e12
    assert pkt.priority == 1
    assert pkt.hops == 2
    assert pkt.path_history == ["pod-1", "relay-a", "relay-b"]
    assert pkt.metadata == {"model": "resnet18"}


def test_packet_is_dataclass():
    assert dataclasses.is_dataclass(Packet)


def test_packet_equality():
    pkt1 = Packet("pkt-001", NodeId("a"), NodeId("b"), 100, "data", 0.0)
    pkt2 = Packet("pkt-001", NodeId("a"), NodeId("b"), 100, "data", 0.0)
    assert pkt1 == pkt2


def test_packet_inequality():
    pkt1 = Packet("pkt-001", NodeId("a"), NodeId("b"), 100, "data", 0.0)
    pkt2 = Packet("pkt-002", NodeId("a"), NodeId("b"), 100, "data", 0.0)
    assert pkt1 != pkt2


def test_packet_default_factories_are_independent():
    pkt1 = Packet("pkt-001", NodeId("a"), NodeId("b"), 100, "data", 0.0)
    pkt2 = Packet("pkt-002", NodeId("a"), NodeId("b"), 100, "data", 0.0)
    pkt1.path_history.append("hop-1")
    pkt1.metadata["key"] = "value"
    assert pkt2.path_history == []
    assert pkt2.metadata == {}
