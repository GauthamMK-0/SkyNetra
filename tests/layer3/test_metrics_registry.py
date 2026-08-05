from __future__ import annotations

import pytest

from skynetra.foundation.errors import ConfigError
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.physics_metrics import PhysicsMetricsCollector
from skynetra.orchestration.metrics.registry import (
    STRATEGIES,
    build_metrics_collectors,
)
from skynetra.orchestration.metrics.topology_metrics import TopologyMetricsCollector


class TestMetricsRegistry:
    def test_strategy_names(self):
        assert set(STRATEGIES) == {
            "network_metrics",
            "compute_metrics",
            "topology_metrics",
            "physics_metrics",
        }

    def test_strategy_class_mapping(self):
        assert STRATEGIES["network_metrics"] is NetworkMetricsCollector
        assert STRATEGIES["compute_metrics"] is ComputeMetricsCollector
        assert STRATEGIES["topology_metrics"] is TopologyMetricsCollector
        assert STRATEGIES["physics_metrics"] is PhysicsMetricsCollector

    def test_build_metrics_collectors_builds_all(self):
        collectors = build_metrics_collectors(
            [
                {"name": "network_metrics"},
                {"name": "compute_metrics"},
                {"name": "topology_metrics"},
                {"name": "physics_metrics", "config": {"tick": 1}},
            ]
        )
        assert [c.name for c in collectors] == [
            "network_metrics",
            "compute_metrics",
            "topology_metrics",
            "physics_metrics",
        ]
        assert collectors[3]._config == {"tick": 1}

    def test_build_metrics_collectors_empty_specs(self):
        assert build_metrics_collectors([]) == []

    def test_build_metrics_collectors_unknown_name_raises(self):
        with pytest.raises(ConfigError, match="Unknown metrics collector 'bogus'"):
            build_metrics_collectors([{"name": "bogus"}])
