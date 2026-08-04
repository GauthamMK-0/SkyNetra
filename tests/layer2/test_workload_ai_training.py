from __future__ import annotations

import pytest
import simpy

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.workload.ai_training import AITrainingSyncWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.registry import STRATEGIES, build_workloads
from skynetra.foundation.errors import ConfigError
from skynetra.foundation.types import NodeId


def _pods(n: int) -> dict[NodeId, Node]:
    return {NodeId(f"p{i}"): PodNode(NodeId(f"p{i}")) for i in range(n)}


def _run(workload, registry: dict[NodeId, Node], until: float):
    env = simpy.Environment()
    sent = []
    env.process(workload.generate(env, sent.append, registry))
    env.run(until=until)
    return sent


class TestAITrainingSyncWorkload:
    def test_is_workload_generator(self):
        assert isinstance(AITrainingSyncWorkload(), WorkloadGenerator)

    def test_all_reduce_packet_count_per_round(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 10.0}
            ),
            _pods(3),
            100.0,
        )
        assert len(sent) == 6

    def test_all_reduce_emits_every_ordered_pair(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 10.0}
            ),
            _pods(3),
            100.0,
        )
        pairs = {(p.src, p.dst) for p in sent}
        expected = {
            (NodeId("p0"), NodeId("p1")),
            (NodeId("p0"), NodeId("p2")),
            (NodeId("p1"), NodeId("p0")),
            (NodeId("p1"), NodeId("p2")),
            (NodeId("p2"), NodeId("p0")),
            (NodeId("p2"), NodeId("p1")),
        }
        assert pairs == expected

    def test_parameter_server_packet_count(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "parameter_server", "rounds": 1, "sync_interval_s": 10.0}
            ),
            _pods(3),
            100.0,
        )
        assert len(sent) == 2

    def test_parameter_server_workers_to_server(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "parameter_server", "rounds": 1, "sync_interval_s": 10.0}
            ),
            _pods(3),
            100.0,
        )
        for p in sent:
            assert p.dst == NodeId("p0")
            assert p.src in (NodeId("p1"), NodeId("p2"))

    def test_rounds_honored(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "all_reduce", "rounds": 2, "sync_interval_s": 10.0}
            ),
            _pods(3),
            100.0,
        )
        assert len(sent) == 12

    def test_emission_after_sync_interval(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 10.0}
            ),
            _pods(3),
            100.0,
        )
        assert all(p.created_at == 10.0 for p in sent)

    def test_packet_fields(self):
        sent = _run(
            AITrainingSyncWorkload(
                {
                    "pattern": "parameter_server",
                    "rounds": 1,
                    "sync_interval_s": 10.0,
                    "gradient_size_bytes": 2048,
                    "priority": 2,
                }
            ),
            _pods(3),
            100.0,
        )
        for p in sent:
            assert p.size_bytes == 2048
            assert p.packet_type == "ai_training_sync"
            assert p.priority == 2

    def test_single_pod_emits_nothing(self):
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 10.0}
            ),
            _pods(1),
            100.0,
        )
        assert sent == []

    def test_faulted_worker_excluded(self):
        registry = _pods(3)
        registry[NodeId("p1")].update_physics({"fault_probability": 1.0})
        sent = _run(
            AITrainingSyncWorkload(
                {"pattern": "all_reduce", "rounds": 1, "sync_interval_s": 10.0}
            ),
            registry,
            100.0,
        )
        assert len(sent) == 2
        assert all(p.src != NodeId("p1") and p.dst != NodeId("p1") for p in sent)

    def test_unknown_pattern_raises(self):
        with pytest.raises(ConfigError):
            AITrainingSyncWorkload({"pattern": "ring"})

    def test_registered(self):
        assert "ai_training_sync" in STRATEGIES
        assert STRATEGIES["ai_training_sync"] is AITrainingSyncWorkload


class TestGetActivePods:
    def test_returns_operational_pods_only(self):
        registry = {
            NodeId("pod-1"): PodNode(NodeId("pod-1")),
            NodeId("pod-2"): PodNode(NodeId("pod-2")),
            NodeId("relay-1"): RelayNode(NodeId("relay-1")),
        }
        registry[NodeId("pod-2")].update_physics({"fault_probability": 1.0})
        workload = AITrainingSyncWorkload()
        assert workload.get_active_pods(registry) == [NodeId("pod-1")]

    def test_empty_registry(self):
        assert AITrainingSyncWorkload().get_active_pods({}) == []

    def test_excludes_relay_nodes(self):
        registry = {
            NodeId("relay-1"): RelayNode(NodeId("relay-1")),
            NodeId("relay-2"): RelayNode(NodeId("relay-2")),
        }
        assert AITrainingSyncWorkload().get_active_pods(registry) == []


class TestWorkloadRegistry:
    def test_strategy_names(self):
        assert set(STRATEGIES.keys()) == {
            "ai_training_sync",
            "inference_query",
            "federated_learning",
        }

    def test_build_known_workloads(self):
        workloads = build_workloads(
            [
                {"name": "ai_training_sync"},
                {"name": "inference_query", "config": {"mean_interval_s": 0.5}},
                {"name": "federated_learning"},
            ]
        )
        assert [type(w).__name__ for w in workloads] == [
            "AITrainingSyncWorkload",
            "InferenceQueryWorkload",
            "FederatedLearningWorkload",
        ]

    def test_build_empty_specs(self):
        assert build_workloads([]) == []

    def test_build_unknown_name_raises(self):
        with pytest.raises(ConfigError) as excinfo:
            build_workloads([{"name": "quantum_teleport"}])
        assert "Unknown workload 'quantum_teleport'" in str(excinfo.value)
