from __future__ import annotations

from typing import Any, Dict, List, Tuple

import networkx as nx
import pytest

from skynetra.domain.nodes.base import Node, PhysicsState, MetricsState
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.ground import GroundStation
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId, Vector3
from skynetra.foundation.eventbus import EventBus


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def sample_vector3() -> Vector3:
    return (1.0, 2.0, 3.0)


@pytest.fixture
def sample_physics_state() -> PhysicsState:
    return PhysicsState(
        position=(7000.0, 0.0, 0.0),
        velocity=(0.0, 7.5, 0.0),
        temperature=280.0,
        radiation_dose=0.5,
        power_available=1000.0,
        power_consumed=500.0,
    )


@pytest.fixture
def sample_metrics_state() -> MetricsState:
    return MetricsState(
        packets_sent=10,
        packets_received=8,
        packets_dropped=2,
        compute_tasks=5,
        compute_flops=1e12,
        energy_consumed=200.0,
    )


@pytest.fixture
def relay_a() -> RelayNode:
    return RelayNode(NodeId("relay-a"))


@pytest.fixture
def relay_b() -> RelayNode:
    return RelayNode(NodeId("relay-b"))


@pytest.fixture
def pod_node() -> PodNode:
    return PodNode(NodeId("pod-1"), flops=2e12, memory_gb=32.0, storage_gb=500.0)


@pytest.fixture
def ground_station() -> GroundStation:
    return GroundStation(NodeId("gs-1"), latitude=37.0, longitude=-122.0, altitude_m=100.0)


@pytest.fixture
def sample_packet() -> Packet:
    return Packet(
        packet_id="pkt-001",
        source=NodeId("relay-a"),
        destination=NodeId("gs-1"),
        size_bytes=1500,
        creation_time=0.0,
    )


@pytest.fixture
def simple_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_node("A", position=(0.0, 0.0, 7000.0))
    g.add_node("B", position=(1000.0, 0.0, 7000.0))
    g.add_node("C", position=(2000.0, 0.0, 7000.0))
    g.add_edge("A", "B", quality=0.9)
    g.add_edge("B", "C", quality=0.8)
    g.add_edge("A", "C", quality=0.1)
    return g


@pytest.fixture
def node_positions() -> Dict[NodeId, Vector3]:
    return {
        NodeId("sat-1"): (7000.0, 0.0, 0.0),
        NodeId("sat-2"): (0.0, 7000.0, 0.0),
        NodeId("sat-3"): (0.0, 0.0, 7000.0),
    }


@pytest.fixture
def sample_nodes_dict(
    relay_a: RelayNode, relay_b: RelayNode, pod_node: PodNode, ground_station: GroundStation
) -> Dict[NodeId, Node]:
    return {
        relay_a.node_id: relay_a,
        relay_b.node_id: relay_b,
        pod_node.node_id: pod_node,
        ground_station.node_id: ground_station,
    }
