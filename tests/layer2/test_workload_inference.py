from __future__ import annotations

import pytest
import simpy

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.engines.workload.inference import InferenceQueryWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
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


def _sequence(packets) -> list[tuple[NodeId, NodeId, float]]:
    return [(p.src, p.dst, round(p.created_at, 6)) for p in packets]


class TestInferenceQueryWorkload:
    def test_is_workload_generator(self):
        assert isinstance(InferenceQueryWorkload(), WorkloadGenerator)

    def test_poisson_emits_within_horizon(self):
        sent = _run(
            InferenceQueryWorkload({"mean_interval_s": 1.0, "seed": 7}),
            _pods(2),
            10.0,
        )
        assert len(sent) > 0
        assert all(p.created_at <= 10.0 for p in sent)

    def test_poisson_emissions_to_active_pods(self):
        sent = _run(
            InferenceQueryWorkload({"mean_interval_s": 1.0, "seed": 7}),
            _pods(2),
            10.0,
        )
        for p in sent:
            assert p.dst in (NodeId("p0"), NodeId("p1"))
            assert p.packet_type == "inference_query"

    def test_poisson_emission_times_monotone(self):
        sent = _run(
            InferenceQueryWorkload({"mean_interval_s": 1.0, "seed": 7}),
            _pods(2),
            10.0,
        )
        times = [p.created_at for p in sent]
        assert times == sorted(times)

    def test_faster_rate_more_packets(self):
        slow = _run(
            InferenceQueryWorkload({"mean_interval_s": 5.0, "seed": 7}),
            _pods(2),
            100.0,
        )
        fast = _run(
            InferenceQueryWorkload({"mean_interval_s": 0.5, "seed": 7}),
            _pods(2),
            100.0,
        )
        assert len(fast) > len(slow)

    def test_on_off_silent_during_off_window(self):
        sent = _run(
            InferenceQueryWorkload(
                {
                    "arrival_pattern": "on_off",
                    "mean_interval_s": 0.2,
                    "on_duration_s": 5.0,
                    "off_duration_s": 10.0,
                    "seed": 1,
                }
            ),
            _pods(2),
            20.0,
        )
        assert all(not (5.0 <= p.created_at < 15.0) for p in sent)
        assert any(p.created_at < 5.0 for p in sent)

    def test_on_off_emits_during_on_window(self):
        sent = _run(
            InferenceQueryWorkload(
                {
                    "arrival_pattern": "on_off",
                    "mean_interval_s": 0.2,
                    "on_duration_s": 5.0,
                    "off_duration_s": 10.0,
                    "seed": 1,
                }
            ),
            _pods(2),
            20.0,
        )
        assert any(p.created_at < 5.0 for p in sent)

    def test_bursty_emits_exact_burst(self):
        sent = _run(
            InferenceQueryWorkload(
                {
                    "arrival_pattern": "bursty",
                    "burst_size": 4,
                    "burst_interval_s": 0.5,
                    "burst_idle_s": 100.0,
                    "seed": 1,
                }
            ),
            _pods(2),
            5.0,
        )
        assert len(sent) == 4
        gaps = [
            sent[i + 1].created_at - sent[i].created_at for i in range(len(sent) - 1)
        ]
        assert all(gap == pytest.approx(0.5) for gap in gaps)

    def test_sources_config_respected(self):
        registry = {
            NodeId("p0"): PodNode(NodeId("p0")),
            NodeId("p1"): PodNode(NodeId("p1")),
            NodeId("gs-1"): PodNode(NodeId("gs-1")),
        }
        sent = _run(
            InferenceQueryWorkload(
                {"mean_interval_s": 0.5, "sources": [NodeId("gs-1")], "seed": 3}
            ),
            registry,
            10.0,
        )
        assert len(sent) > 0
        assert all(p.src == NodeId("gs-1") for p in sent)

    def test_no_pods_emits_nothing(self):
        registry = {NodeId("relay-1"): PodNode(NodeId("relay-1"))}
        registry[NodeId("relay-1")].update_physics({"fault_probability": 1.0})
        sent = _run(
            InferenceQueryWorkload({"mean_interval_s": 0.5, "seed": 3}),
            registry,
            10.0,
        )
        assert sent == []

    def test_unknown_pattern_raises(self):
        with pytest.raises(ConfigError):
            InferenceQueryWorkload({"arrival_pattern": "zigzag"})


class TestInferenceReproducibility:
    def test_same_seed_identical_sequence(self):
        registry = _pods(2)
        config = {"mean_interval_s": 0.7, "seed": 42}
        first = _sequence(_run(InferenceQueryWorkload(config), registry, 10.0))
        second = _sequence(_run(InferenceQueryWorkload(config), registry, 10.0))
        assert first == second

    def test_different_seed_different_sequence(self):
        registry = _pods(2)
        base = _sequence(
            _run(InferenceQueryWorkload({"mean_interval_s": 0.7, "seed": 42}), registry, 10.0)
        )
        other = _sequence(
            _run(InferenceQueryWorkload({"mean_interval_s": 0.7, "seed": 43}), registry, 10.0)
        )
        assert base != other
