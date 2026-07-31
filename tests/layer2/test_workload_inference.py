from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStation
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.workload.inference import InferenceWorkload
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.foundation.types import NodeId, TimeSeconds


class TestInferenceWorkload:
    def test_name(self):
        profile = WorkloadProfile(name="inference")
        wl = InferenceWorkload(profile, ground_nodes=[NodeId("gs-1")])
        assert wl.name() == "inference"

    def test_generate_with_space_and_ground(self):
        profile = WorkloadProfile(name="inference", packet_size_bytes=256)
        wl = InferenceWorkload(profile, ground_nodes=[NodeId("gs-1")])
        nodes: Dict[NodeId, Node] = {
            NodeId("gs-1"): GroundStation(NodeId("gs-1")),
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert len(packets) == 1
        assert packets[0].source == "gs-1"
        assert packets[0].destination == "sat-1"

    def test_generate_multiple_space_nodes(self):
        profile = WorkloadProfile(name="inference")
        wl = InferenceWorkload(profile, ground_nodes=[NodeId("gs-1")])
        nodes: Dict[NodeId, Node] = {
            NodeId("gs-1"): GroundStation(NodeId("gs-1")),
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
            NodeId("sat-2"): RelayNode(NodeId("sat-2")),
        }
        packets = wl.generate(TimeSeconds(1.0), nodes)
        assert len(packets) == 2

    def test_no_ground_nodes_returns_empty(self):
        profile = WorkloadProfile(name="inference")
        wl = InferenceWorkload(profile, ground_nodes=[])
        nodes: Dict[NodeId, Node] = {
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert packets == []

    def test_no_space_nodes_returns_empty(self):
        profile = WorkloadProfile(name="inference")
        wl = InferenceWorkload(profile, ground_nodes=[NodeId("gs-1")])
        nodes: Dict[NodeId, Node] = {
            NodeId("gs-1"): GroundStation(NodeId("gs-1")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert packets == []

    def test_generated_packet_properties(self):
        profile = WorkloadProfile(name="inference", packet_size_bytes=512, ttl=16, priority=3)
        wl = InferenceWorkload(profile, ground_nodes=[NodeId("gs-1")])
        nodes: Dict[NodeId, Node] = {
            NodeId("gs-1"): GroundStation(NodeId("gs-1")),
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        packets = wl.generate(TimeSeconds(10.0), nodes)
        for pkt in packets:
            assert pkt.size_bytes == 512
            assert pkt.ttl == 16
            assert pkt.priority == 3
            assert pkt.creation_time == 10.0

    def test_multiple_ground_nodes(self):
        profile = WorkloadProfile(name="inference")
        wl = InferenceWorkload(profile, ground_nodes=[NodeId("gs-1"), NodeId("gs-2")])
        nodes: Dict[NodeId, Node] = {
            NodeId("gs-1"): GroundStation(NodeId("gs-1")),
            NodeId("gs-2"): GroundStation(NodeId("gs-2")),
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert len(packets) == 2

    def test_is_workload_generator(self):
        from skynetra.engines.workload.interface import WorkloadGenerator
        profile = WorkloadProfile(name="inference")
        assert isinstance(
            InferenceWorkload(profile, ground_nodes=[NodeId("gs-1")]),
            WorkloadGenerator,
        )

    def test_registered(self):
        from skynetra.engines.workload.registry import STRATEGIES
        assert "inference" in STRATEGIES
        assert STRATEGIES["inference"] is InferenceWorkload
