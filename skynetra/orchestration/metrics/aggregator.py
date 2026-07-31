"""
Orchestration layer (L3) — metrics aggregator.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any, Dict, List

from skynetra.orchestration.context import SimulationContext
from skynetra.orchestration.metrics.interface import MetricsCollector


class MetricsAggregator:
    def __init__(self, collectors: List[MetricsCollector]) -> None:
        self._collectors = collectors

    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for collector in self._collectors:
            result[collector.name()] = collector.collect(context)
        return result
