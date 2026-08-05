"""
Orchestration layer (L3) — metrics collector static registry.

Static strategy registry — NOT dynamically discovered.

Extending: add your class + import + dict entry, or instantiate a
MetricsCollector directly and pass it to the aggregator without ever
touching this file.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.foundation.errors import ConfigError
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.physics_metrics import PhysicsMetricsCollector
from skynetra.orchestration.metrics.topology_metrics import TopologyMetricsCollector

STRATEGIES: dict[str, type[MetricsCollector]] = {
    "network_metrics": NetworkMetricsCollector,
    "compute_metrics": ComputeMetricsCollector,
    "topology_metrics": TopologyMetricsCollector,
    "physics_metrics": PhysicsMetricsCollector,
}


def build_metrics_collectors(specs: list[dict[str, Any]]) -> list[MetricsCollector]:
    """specs = [{"name": "network_metrics", "config": {...}}, ...]"""
    out: list[MetricsCollector] = []
    for spec in specs:
        cls = STRATEGIES.get(spec["name"])
        if cls is None:
            raise ConfigError(f"Unknown metrics collector '{spec['name']}'")
        out.append(cls(spec.get("config", {})))
    return out
