"""
How to write and use a custom `MetricsCollector` at the orchestration
layer: `LatencyMetricsCollector` tallies hops from live
`PacketTransmitEvent`s on the EventBus.

It implements the three ABC methods (`attach`, `get_summary`,
`to_dataframe`), gets registered in the L3 strategy registry, and is
then selectable through the L4 `FullConfig` metrics list.

Run:  python examples/custom_metrics_collector.py
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from skynetra.foundation.eventbus import EventBus
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import PacketTransmitEvent
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class LatencyMetricsCollector(MetricsCollector):
    name: str = "latency_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._transmits = 0

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(PacketTransmitEvent, self._on_transmit)

    def _on_transmit(self, event: PacketTransmitEvent) -> None:
        self._transmits += 1

    def get_summary(self) -> dict[str, Any]:
        return {"estimated_total_hops": self._transmits}

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._transmits = 0


def main() -> None:
    STRATEGIES["latency_metrics"] = LatencyMetricsCollector

    config = FullConfig(
        simulation={"duration_s": 30.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6},
        pods={"n_pods": 2},
        workload={"active": ["inference_query"], "inference_query": {"arrival_rate_rps": 2.0}},
        metrics={"active": ["network_metrics", "latency_metrics"]},
    )

    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    print(f"Custom LatencyMetricsCollector simulation: {results.duration}s")
    print(f"Metrics: {results.engine_metrics}")


if __name__ == "__main__":
    main()
