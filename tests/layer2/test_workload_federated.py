from __future__ import annotations

from typing import Dict

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.foundation.types import NodeId, TimeSeconds


class TestFederatedLearningWorkload:
    def test_name(self):
        profile = WorkloadProfile(name="federated")
        wl = FederatedLearningWorkload(profile, aggregator=NodeId("agg"))
        assert wl.name() == "federated_learning"

    def test_generate_two_nodes(self):
        profile = WorkloadProfile(name="federated", packet_size_bytes=2048)
        wl = FederatedLearningWorkload(profile, aggregator=NodeId("agg"))
        nodes: Dict[NodeId, Node] = {
            NodeId("agg"): PodNode(NodeId("agg")),
            NodeId("worker-1"): PodNode(NodeId("worker-1")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert len(packets) == 1
        assert packets[0].source == "worker-1"
        assert packets[0].destination == "agg"

    def test_generate_multiple_workers(self):
        profile = WorkloadProfile(name="federated")
        wl = FederatedLearningWorkload(profile, aggregator=NodeId("agg"))
        nodes: Dict[NodeId, Node] = {
            NodeId("agg"): PodNode(NodeId("agg")),
            NodeId("w1"): PodNode(NodeId("w1")),
            NodeId("w2"): PodNode(NodeId("w2")),
            NodeId("w3"): PodNode(NodeId("w3")),
        }
        packets = wl.generate(TimeSeconds(1.0), nodes)
        assert len(packets) == 3

    def test_aggregator_excluded(self):
        profile = WorkloadProfile(name="federated")
        wl = FederatedLearningWorkload(profile, aggregator=NodeId("agg"))
        nodes: Dict[NodeId, Node] = {
            NodeId("agg"): PodNode(NodeId("agg")),
        }
        packets = wl.generate(TimeSeconds(0.0), nodes)
        assert packets == []

    def test_generated_packet_properties(self):
        profile = WorkloadProfile(name="federated", packet_size_bytes=4096, ttl=32, priority=1)
        wl = FederatedLearningWorkload(profile, aggregator=NodeId("agg"))
        nodes: Dict[NodeId, Node] = {
            NodeId("agg"): PodNode(NodeId("agg")),
            NodeId("worker"): PodNode(NodeId("worker")),
        }
        packets = wl.generate(TimeSeconds(5.0), nodes)
        for pkt in packets:
            assert pkt.size_bytes == 4096
            assert pkt.ttl == 32
            assert pkt.priority == 1
            assert pkt.creation_time == 5.0
            assert pkt.destination == "agg"

    def test_empty_nodes(self):
        profile = WorkloadProfile(name="federated")
        wl = FederatedLearningWorkload(profile, aggregator=NodeId("agg"))
        packets = wl.generate(TimeSeconds(0.0), {})
        assert packets == []

    def test_is_workload_generator(self):
        from skynetra.engines.workload.interface import WorkloadGenerator
        profile = WorkloadProfile(name="federated")
        assert isinstance(FederatedLearningWorkload(profile, aggregator=NodeId("agg")), WorkloadGenerator)

    def test_registered(self):
        from skynetra.engines.workload.registry import STRATEGIES
        assert "federated_learning" in STRATEGIES
        assert STRATEGIES["federated_learning"] is FederatedLearningWorkload
