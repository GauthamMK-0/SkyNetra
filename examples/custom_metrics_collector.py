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

from collections import Counter, defaultdict
from typing import Any

import pandas as pd

from skynetra.foundation.eventbus import EventBus
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import (
    PacketDeliveredEvent,
    PacketDropEvent,
    PacketTransmitEvent,
)
from skynetra.orchestration.metrics.interface import MetricsCollector
from skynetra.orchestration.metrics.registry import STRATEGIES


class HopCountMetricsCollector(MetricsCollector):
    """Custom collector: subscribes to transmit, delivery, and drop events to measure
    aggregate hops, per-packet path lengths, and path distribution statistics.
    """

    name: str = "hop_metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._transmits = 0
        self._deliveries = 0
        self._drops = 0
        self._packet_hops: dict[str, int] = defaultdict(int)
        self._delivered_hops: list[int] = []

    def attach(self, event_bus: EventBus) -> None:
        event_bus.subscribe(PacketTransmitEvent, self._on_transmit)
        event_bus.subscribe(PacketDeliveredEvent, self._on_delivered)
        event_bus.subscribe(PacketDropEvent, self._on_drop)

    def _on_transmit(self, event: PacketTransmitEvent) -> None:
        self._transmits += 1
        self._packet_hops[event.packet.packet_id] += 1

    def _on_delivered(self, event: PacketDeliveredEvent) -> None:
        self._deliveries += 1
        hops = self._packet_hops.get(event.packet.packet_id, 1)
        self._delivered_hops.append(hops)

    def _on_drop(self, event: PacketDropEvent) -> None:
        self._drops += 1

    def get_summary(self) -> dict[str, Any]:
        avg_hops = (
            sum(self._delivered_hops) / len(self._delivered_hops)
            if self._delivered_hops
            else 0.0
        )
        min_hops = min(self._delivered_hops) if self._delivered_hops else 0
        max_hops = max(self._delivered_hops) if self._delivered_hops else 0
        hop_dist = dict(sorted(Counter(self._delivered_hops).items()))
        return {
            "total_transmits": self._transmits,
            "total_deliveries": self._deliveries,
            "total_drops": self._drops,
            "avg_hops_per_packet": round(avg_hops, 2),
            "min_hops": min_hops,
            "max_hops": max_hops,
            "hop_distribution": hop_dist,
        }

    def to_dataframe(self) -> pd.DataFrame:
        summary = self.get_summary()
        summary["hop_distribution"] = str(summary["hop_distribution"])
        return pd.DataFrame([summary])

    def reset(self) -> None:
        self._transmits = 0
        self._deliveries = 0
        self._drops = 0
        self._packet_hops.clear()
        self._delivered_hops.clear()


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

    print("Running Custom Metrics Collector Simulation (60.0s)...")
    results = OrbitDCSimulation.from_spec(config_to_simulation_spec(config)).run()

    net = results.engine_metrics.get("network_metrics", {})
    hops = results.engine_metrics.get("hop_metrics", {})

    transmitted = net.get("transmitted", 0)
    delivered = net.get("delivered", 0)
    dropped = net.get("dropped", 0)
    drop_rate = (dropped / max(1, transmitted)) * 100
    delivery_rate = (delivered / max(1, delivered + dropped)) * 100
    avg_latency_ms = net.get("avg_latency_s", 0.0) * 1000

    print("\n" + "=" * 70)
    print("               SKYNETRA CUSTOM METRICS COLLECTOR REPORT               ")
    print("=" * 70)
    print("Scenario Configuration:")
    print(f"  * Simulation Duration : {results.duration:.1f} simulated seconds")
    print("  * Constellation       : Walker-Delta 3 planes x 6 satellites (18 total)")
    print("  * Compute Infrastructure: 2 On-Orbit Pods")
    print("  * Ground Infrastructure : 1 Ground Station (>= 10.0 deg elevation)")
    print("  * Workload Profile    : Poisson Inference Queries (mean interval = 2.5s)")

    print("\n[Standard Built-in Network Metrics]")
    print(f"  * Packets Injected/Transmitted : {transmitted}")
    print(f"  * Packets Successfully Delivered : {delivered}")
    print(f"  * Packets Dropped (Congestion/No Route): {dropped}")
    print(f"  * Mean End-to-End Latency        : {avg_latency_ms:.2f} ms")
    print(f"  * Overall Packet Loss Rate       : {drop_rate:.2f}%")
    print(f"  * Delivery Completion Rate       : {delivery_rate:.2f}%")

    print("\n[Custom HopCountMetricsCollector (Hop Path Analysis)]")
    print(f"  * Total Forwarding Hops       : {hops.get('total_transmits', 0)}")
    print(f"  * Delivered Sessions          : {hops.get('total_deliveries', 0)}")
    avg_hops = hops.get('avg_hops_per_packet', 0.0)
    print(f"  * Average Path Length         : {avg_hops:.2f} hops/packet")
    print(f"  * Shortest Completed Path     : {hops.get('min_hops', 0)} hops")
    print(f"  * Longest Completed Path      : {hops.get('max_hops', 0)} hops")

    hop_dist = hops.get("hop_distribution", {})
    if hop_dist:
        print("  * Path Length Distribution:")
        for h, count in hop_dist.items():
            pct = (count / max(1, delivered)) * 100
            print(f"      - {h} hops : {count:>2} packets ({pct:>5.1f}%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
