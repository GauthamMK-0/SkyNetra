from __future__ import annotations

from skynetra.domain.nodes.base import Node, PhysicsState, MetricsState
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.ground import GroundStation
from skynetra.foundation.types import NodeId


class TestRelayNode:
    def test_creation(self):
        node = RelayNode(NodeId("relay-1"))
        assert node.node_id == "relay-1"
        assert node.node_type == "relay"

    def test_physics_default(self):
        node = RelayNode(NodeId("relay-1"))
        assert isinstance(node.physics, PhysicsState)

    def test_metrics_default(self):
        node = RelayNode(NodeId("relay-1"))
        assert isinstance(node.metrics, MetricsState)

    def test_step(self):
        node = RelayNode(NodeId("relay-1"))
        node.step(1.0)


class TestPodNode:
    def test_creation_defaults(self):
        node = PodNode(NodeId("pod-1"))
        assert node.node_id == "pod-1"
        assert node.node_type == "pod"
        assert node.flops == 1e12
        assert node.memory_gb == 16.0
        assert node.storage_gb == 100.0

    def test_creation_custom(self):
        node = PodNode(NodeId("pod-2"), flops=2e12, memory_gb=32.0, storage_gb=500.0)
        assert node.flops == 2e12
        assert node.memory_gb == 32.0
        assert node.storage_gb == 500.0

    def test_physics_default(self):
        node = PodNode(NodeId("pod-1"))
        assert isinstance(node.physics, PhysicsState)

    def test_metrics_default(self):
        node = PodNode(NodeId("pod-1"))
        assert isinstance(node.metrics, MetricsState)

    def test_step(self):
        node = PodNode(NodeId("pod-1"))
        node.step(1.0)

    def test_properties_immutable_by_convention(self):
        node = PodNode(NodeId("pod-1"))
        assert node.flops == node._flops
        assert node.memory_gb == node._memory_gb
        assert node.storage_gb == node._storage_gb


class TestGroundStation:
    def test_creation_defaults(self):
        gs = GroundStation(NodeId("gs-1"))
        assert gs.node_id == "gs-1"
        assert gs.node_type == "ground"
        assert gs.latitude == 0.0
        assert gs.longitude == 0.0
        assert gs.altitude_m == 0.0

    def test_creation_custom(self):
        gs = GroundStation(NodeId("gs-2"), latitude=37.0, longitude=-122.0, altitude_m=100.0)
        assert gs.latitude == 37.0
        assert gs.longitude == -122.0
        assert gs.altitude_m == 100.0

    def test_physics_default(self):
        gs = GroundStation(NodeId("gs-1"))
        assert isinstance(gs.physics, PhysicsState)

    def test_metrics_default(self):
        gs = GroundStation(NodeId("gs-1"))
        assert isinstance(gs.metrics, MetricsState)

    def test_step(self):
        gs = GroundStation(NodeId("gs-1"))
        gs.step(1.0)

    def test_is_node(self):
        gs = GroundStation(NodeId("gs-1"))
        assert isinstance(gs, Node)
