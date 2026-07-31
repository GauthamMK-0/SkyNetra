"""
Orchestration layer (L3) — static metrics collector registry.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict, Type

from skynetra.orchestration.metrics.interface import MetricsCollector

STRATEGIES: Dict[str, Type[MetricsCollector]] = {}


def get_metrics_collector(name: str, **kwargs: object) -> MetricsCollector:
    cls = STRATEGIES.get(name)
    if cls is None:
        raise KeyError(f"Unknown metrics collector: {name}")
    return cls(**kwargs)


def list_metrics_collectors() -> list[str]:
    return list(STRATEGIES.keys())
