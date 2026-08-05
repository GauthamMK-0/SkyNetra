"""
Orchestration layer (L3) — topology metrics collector.

Event-driven: subscribes to `TopologyUpdateEvent` and records the number
of topology refreshes plus the latest reported graph size and version.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.events import TopologyUpdateEvent
from skynetra.orchestration.metrics.interface import MetricsCollector


class TopologyMetricsCollector(MetricsCollector):
    """Topology refresh count and latest graph state from live events."""

    name: str = "topology_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._updates = 0
        self._latest_version = 0
        self._latest_node_count = 0
        self._latest_edge_count = 0

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(TopologyUpdateEvent, self._on_topology_update)

    def _on_topology_update(self, event: TopologyUpdateEvent) -> None:
        self._updates += 1
        self._latest_version = event.topology_version
        self._latest_node_count = event.node_count
        self._latest_edge_count = event.edge_count

    def get_summary(self) -> dict[str, Any]:
        return {
            "topology_updates": self._updates,
            "latest_topology_version": self._latest_version,
            "final_node_count": self._latest_node_count,
            "final_edge_count": self._latest_edge_count,
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._updates = 0
        self._latest_version = 0
        self._latest_node_count = 0
        self._latest_edge_count = 0
