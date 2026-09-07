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
from skynetra.orchestration.events import PacketDeliveredEvent, PacketTransmitEvent
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class HopCountMetricsCollector(MetricsCollector):
    """Custom collector: subscribes to transmit and delivery events to measure
    aggregate hops and average hops per successfully delivered packet.
    """

    name: str = "hop_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._transmits = 0
        self._deliveries = 0

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(PacketTransmitEvent, self._on_transmit)
        event_bus.subscribe(PacketDeliveredEvent, self._on_delivered)

    def _on_transmit(self, event: PacketTransmitEvent) -> None:
        self._transmits += 1

    def _on_delivered(self, event: PacketDeliveredEvent) -> None:
        self._deliveries += 1

    def get_summary(self) -> dict[str, Any]:
        avg_hops = self._transmits / max(1, self._deliveries)
        return {
            "total_transmits": self._transmits,
            "total_deliveries": self._deliveries,
            "avg_hops_per_packet": round(avg_hops, 2),
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.get_summary()])

    def reset(self) -> None:
        self._transmits = 0
        self._deliveries = 0


def main() -> None:
    # Register the custom collector in Layer 3 strategy registry
    STRATEGIES["hop_metrics"] = HopCountMetricsCollector

    config = FullConfig(
        simulation={"duration_s": 60.0, "seed": 42},
        constellation={"n_planes": 3, "sats_per_plane": 6},
        pods={"n_pods": 2},
        ground_stations={"n_ground_stations": 1, "gsl_elevation_min_deg": 10.0},
        workload={
            "active": ["inference_query"],
            "inference_query": {
                "mean_interval_s": 2.5,
                "query_size_bytes": 1024,
                "flops_required": 1e9,
            },
        },
        metrics={"active": ["network_metrics", "hop_metrics"]},
    )

    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    print(f"Custom HopCountMetricsCollector Simulation ({results.duration:.1f}s):")
    net = results.engine_metrics.get("network_metrics", {})
    hops = results.engine_metrics.get("hop_metrics", {})

    print(
        f"  Standard Network : transmitted={net.get('transmitted', 0)} | "
        f"delivered={net.get('delivered', 0)} | "
        f"avg_latency={net.get('avg_latency_s', 0.0) * 1000:.2f} ms"
    )
    print(
        f"  Custom Metric    : total_transmits={hops.get('total_transmits', 0)} | "
        f"total_deliveries={hops.get('total_deliveries', 0)} | "
        f"avg_hops_per_packet={hops.get('avg_hops_per_packet', 0.0)}"
    )


if __name__ == "__main__":
    main()
