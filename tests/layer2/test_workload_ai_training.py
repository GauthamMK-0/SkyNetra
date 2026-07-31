from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.workload.ai_training import AITrainingWorkload
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.foundation.types import NodeId, TimeSeconds


class TestAITrainingWorkload:
    def test_name(self):
        profile = WorkloadProfile(name="training")
        wl = AITrainingWorkload(profile)
        assert wl.name() == "ai_training"

    def test_generate_with_two_nodes(self):
        profile = WorkloadProfile(name="training", packet_size_bytes=512, ttl=64, priority=1)
        wl = AITrainingWorkload(profile)
        nodes: Dict[NodeId, Node] = {
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
            NodeId("sat-2"): RelayNode(NodeId("sat-2")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert len(packets) == 2

    def test_generate_three_nodes(self):
        profile = WorkloadProfile(name="training")
        wl = AITrainingWorkload(profile)
        nodes: Dict[NodeId, Node] = {
            NodeId("a"): RelayNode(NodeId("a")),
            NodeId("b"): RelayNode(NodeId("b")),
            NodeId("c"): RelayNode(NodeId("c")),
        }
        packets = wl.generate(TimeSeconds(1.0), nodes)
        assert len(packets) == 6

    def test_generate_single_node_returns_empty(self):
        profile = WorkloadProfile(name="training")
        wl = AITrainingWorkload(profile)
        nodes: Dict[NodeId, Node] = {
            NodeId("sat-1"): RelayNode(NodeId("sat-1")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert packets == []

    def test_generate_empty_nodes(self):
        profile = WorkloadProfile(name="training")
        wl = AITrainingWorkload(profile)
        packets = wl.generate(TimeSeconds(0.0), {})
        assert packets == []

    def test_generated_packet_properties(self):
        profile = WorkloadProfile(name="training", packet_size_bytes=1024, ttl=32, priority=2)
        wl = AITrainingWorkload(profile)
        nodes: Dict[NodeId, Node] = {
            NodeId("a"): RelayNode(NodeId("a")),
            NodeId("b"): RelayNode(NodeId("b")),
        }
        packets = wl.generate(TimeSeconds(42.0), nodes)
        for pkt in packets:
            assert pkt.size_bytes == 1024
            assert pkt.ttl == 32
            assert pkt.priority == 2
            assert pkt.creation_time == 42.0
            assert pkt.packet_id is not None

    def test_is_workload_generator(self):
        from skynetra.engines.workload.interface import WorkloadGenerator
        profile = WorkloadProfile(name="training")
        assert isinstance(AITrainingWorkload(profile), WorkloadGenerator)

    def test_registered(self):
        from skynetra.engines.workload.registry import STRATEGIES
        assert "ai_training" in STRATEGIES
        assert STRATEGIES["ai_training"] is AITrainingWorkload
