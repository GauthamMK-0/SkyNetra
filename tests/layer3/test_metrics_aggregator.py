from __future__ import annotations

import pytest

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId
from skynetra.orchestration.events import (
    PacketDeliveredEvent,
    PacketDropEvent,
    PacketTransmitEvent,
    TopologyUpdateEvent,
)
from skynetra.orchestration.metrics.aggregator import MetricsAggregator
from skynetra.orchestration.metrics.network import NetworkMetricsCollector
from skynetra.orchestration.metrics.topology_metrics import TopologyMetricsCollector


def _packet(packet_id: str) -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("a"),
        dst=NodeId("b"),
        size_bytes=100,
        packet_type="data",
        created_at=0.0,
    )


def _network_aggregator(
    delivered: int, dropped: int, transmitted: int, latency: float = 0.5
) -> MetricsAggregator:
    bus = EventBus()
    collector = NetworkMetricsCollector()
    aggregator = MetricsAggregator([collector], bus)
    for i in range(delivered):
        bus.publish(
            PacketDeliveredEvent(
                time=1.0,
                event_type="packet_delivered",
                packet=_packet(f"d{i}"),
                node_id=NodeId("b"),
                latency_s=latency,
            )
        )
    for i in range(dropped):
        bus.publish(
            PacketDropEvent(
                time=2.0,
                event_type="packet_drop",
                packet=_packet(f"r{i}"),
                node_id=NodeId("a"),
                reason="no_route",
            )
        )
    for i in range(transmitted):
        bus.publish(
            PacketTransmitEvent(
                time=3.0,
                event_type="packet_transmit",
                packet=_packet(f"t{i}"),
                node_id=NodeId("a"),
                to_node=NodeId("b"),
            )
        )
    return aggregator


class TestMetricsAggregator:
    def test_constructor_attaches_collectors(self):
        bus = EventBus()
        collector = NetworkMetricsCollector()
        MetricsAggregator([collector], bus)

        bus.publish(
            PacketDeliveredEvent(
                time=1.0,
                event_type="packet_delivered",
                packet=_packet("p1"),
                node_id=NodeId("b"),
                latency_s=0.5,
            )
        )
        assert collector.get_summary()["delivered"] == 1

    def test_get_all_summaries_keyed_by_name(self):
        bus = EventBus()
        aggregator = MetricsAggregator([NetworkMetricsCollector(), TopologyMetricsCollector()], bus)
        summaries = aggregator.get_all_summaries()
        assert set(summaries) == {"network_metrics", "topology_metrics"}
        assert "delivered" in summaries["network_metrics"]
        assert "topology_updates" in summaries["topology_metrics"]

    def test_get_combined_summary_flattens_with_prefixes(self):
        bus = EventBus()
        aggregator = MetricsAggregator([TopologyMetricsCollector()], bus)
        bus.publish(
            TopologyUpdateEvent(
                time=10.0,
                event_type="topology_update",
                topology_version=1,
                edge_count=4,
                node_count=3,
            )
        )
        combined = aggregator.get_combined_summary()
        assert combined["topology_metrics.topology_updates"] == 1
        assert combined["topology_metrics.final_node_count"] == 3
        assert combined["topology_metrics.final_edge_count"] == 4

    def test_compare_delta_and_pct_change(self):
        fewer = _network_aggregator(delivered=10, dropped=0, transmitted=10)
        more = _network_aggregator(delivered=15, dropped=5, transmitted=20)

        diffs = more.compare(fewer)
        assert "network_metrics" in diffs
        delivered_diff = diffs["network_metrics"]["delivered"]
        assert delivered_diff["delta"] == 5
        assert delivered_diff["pct_change"] == 50.0

        dropped_diff = diffs["network_metrics"]["dropped"]
        assert dropped_diff["delta"] == 5
        assert dropped_diff["pct_change"] is None  # fewer baseline is 0

        transmitted_diff = diffs["network_metrics"]["transmitted"]
        assert transmitted_diff["delta"] == 10
        assert transmitted_diff["pct_change"] == 100.0

    def test_compare_is_symmetric_direction(self):
        fewer = _network_aggregator(delivered=10, dropped=0, transmitted=10)
        more = _network_aggregator(delivered=15, dropped=0, transmitted=10)

        diffs = fewer.compare(more)
        assert diffs["network_metrics"]["delivered"]["delta"] == -5
        assert diffs["network_metrics"]["delivered"]["pct_change"] == pytest.approx(-100.0 / 3.0)

    def test_compare_identical_aggregators_is_empty(self):
        first = _network_aggregator(delivered=4, dropped=1, transmitted=5)
        second = _network_aggregator(delivered=4, dropped=1, transmitted=5)
        assert first.compare(second) == {}

    def test_compare_with_missing_collectors(self):
        first = _network_aggregator(delivered=3, dropped=0, transmitted=3)
        second = MetricsAggregator([], EventBus())
        diffs = first.compare(second)
        assert "network_metrics" in diffs
        assert diffs["network_metrics"]["delivered"]["delta"] == 3

    def test_export_all_writes_csv_per_collector(self, tmp_path):
        bus = EventBus()
        aggregator = MetricsAggregator([NetworkMetricsCollector(), TopologyMetricsCollector()], bus)
        aggregator.export_all(str(tmp_path))

        files = sorted(p.name for p in tmp_path.iterdir())
        assert files == ["network_metrics.csv", "topology_metrics.csv"]
        content = (tmp_path / "network_metrics.csv").read_text()
        assert "delivered" in content
        assert "drop_rate" in content

    def test_export_all_creates_missing_directory(self, tmp_path):
        bus = EventBus()
        aggregator = MetricsAggregator([NetworkMetricsCollector()], bus)
        target = tmp_path / "nested" / "out"
        aggregator.export_all(str(target))
        assert (target / "network_metrics.csv").is_file()

    def test_reset_all_clears_every_collector(self):
        aggregator = _network_aggregator(delivered=2, dropped=1, transmitted=3)
        assert aggregator.get_all_summaries()["network_metrics"]["delivered"] == 2

        aggregator.reset_all()
        summary = aggregator.get_all_summaries()["network_metrics"]
        assert summary["delivered"] == 0
        assert summary["dropped"] == 0
        assert summary["transmitted"] == 0
