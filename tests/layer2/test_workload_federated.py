from __future__ import annotations

import simpy

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.registry import STRATEGIES
from skynetra.foundation.types import NodeId


def _pods(n: int) -> dict[NodeId, Node]:
    return {NodeId(f"p{i}"): PodNode(NodeId(f"p{i}")) for i in range(n)}


def _run(workload, registry: dict[NodeId, Node], until: float):
    env = simpy.Environment()
    sent = []
    env.process(workload.generate(env, sent.append, registry))
    env.run(until=until)
    return sent


class TestFederatedLearningWorkload:
    def test_is_workload_generator(self):
        assert isinstance(FederatedLearningWorkload(), WorkloadGenerator)

    def test_three_phase_round_sequence(self):
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 1,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 5.0,
                }
            ),
            _pods(3),
            100.0,
        )
        assert [p.packet_type for p in sent] == [
            "fl_gather",
            "fl_gather",
            "fl_broadcast",
            "fl_broadcast",
        ]

    def test_gather_workers_to_aggregator(self):
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 1,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 5.0,
                }
            ),
            _pods(3),
            100.0,
        )
        gathers = [p for p in sent if p.packet_type == "fl_gather"]
        assert all(p.dst == NodeId("p0") for p in gathers)
        assert {p.src for p in gathers} == {NodeId("p1"), NodeId("p2")}

    def test_broadcast_aggregator_to_workers(self):
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 1,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 5.0,
                }
            ),
            _pods(3),
            100.0,
        )
        broadcasts = [p for p in sent if p.packet_type == "fl_broadcast"]
        assert all(p.src == NodeId("p0") for p in broadcasts)
        assert {p.dst for p in broadcasts} == {NodeId("p1"), NodeId("p2")}

    def test_gather_then_aggregate_then_broadcast_timing(self):
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 1,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 5.0,
                }
            ),
            _pods(3),
            100.0,
        )
        assert all(p.created_at == 10.0 for p in sent if p.packet_type == "fl_gather")
        assert all(
            p.created_at == 15.0 for p in sent if p.packet_type == "fl_broadcast"
        )

    def test_rounds_honored(self):
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 3,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 1.0,
                }
            ),
            _pods(3),
            1000.0,
        )
        assert len(sent) == 12
        assert sum(1 for p in sent if p.packet_type == "fl_gather") == 6
        assert sum(1 for p in sent if p.packet_type == "fl_broadcast") == 6

    def test_default_aggregator_is_first_active_pod(self):
        sent = _run(
            FederatedLearningWorkload(
                {"n_rounds": 1, "round_interval_s": 10.0, "aggregate_time_s": 5.0}
            ),
            _pods(3),
            100.0,
        )
        for p in sent:
            if p.packet_type == "fl_gather":
                assert p.dst == NodeId("p0")

    def test_faulted_aggregator_falls_back(self):
        registry = _pods(3)
        registry[NodeId("p0")].update_physics({"fault_probability": 1.0})
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 1,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 5.0,
                }
            ),
            registry,
            100.0,
        )
        for p in sent:
            assert p.src != NodeId("p0") and p.dst != NodeId("p0")
        assert any(p.packet_type == "fl_gather" for p in sent)

    def test_aggregator_only_emits_nothing(self):
        registry = {NodeId("p0"): PodNode(NodeId("p0"))}
        sent = _run(
            FederatedLearningWorkload(
                {
                    "n_rounds": 1,
                    "aggregator": NodeId("p0"),
                    "round_interval_s": 10.0,
                    "aggregate_time_s": 5.0,
                }
            ),
            registry,
            100.0,
        )
        assert sent == []

    def test_no_active_pods_emits_nothing(self):
        registry = {NodeId("p0"): PodNode(NodeId("p0"))}
        registry[NodeId("p0")].update_physics({"fault_probability": 1.0})
        sent = _run(
            FederatedLearningWorkload(
                {"n_rounds": 1, "round_interval_s": 10.0, "aggregate_time_s": 5.0}
            ),
            registry,
            100.0,
        )
        assert sent == []

    def test_registered(self):
        assert "federated_learning" in STRATEGIES
        assert STRATEGIES["federated_learning"] is FederatedLearningWorkload
