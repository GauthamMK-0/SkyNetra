from __future__ import annotations

import pytest

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId
from skynetra.orchestration.events import (
    ComputeJobCompleteEvent,
    PacketDropEvent,
)
from skynetra.orchestration.metrics.compute import ComputeMetricsCollector


def _compute_packet(packet_id: str, flops: float = 1000.0) -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("sat-1"),
        dst=NodeId("pod-1"),
        size_bytes=200,
        packet_type="inference_query",
        created_at=0.0,
        flops_required=flops,
    )


def _attach(bus: EventBus) -> ComputeMetricsCollector:
    collector = ComputeMetricsCollector()
    collector.attach(bus)
    return collector


class TestComputeMetricsCollector:
    def test_name(self):
        assert ComputeMetricsCollector().name == "compute_metrics"

    def test_starts_at_zero(self):
        summary = _attach(EventBus()).get_summary()
        assert summary["compute_jobs_completed"] == 0
        assert summary["compute_flops_completed"] == 0.0
        assert summary["compute_drops"] == 0
        assert summary["jobs_by_pod"] == {}

    def test_accumulates_job_completions(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            ComputeJobCompleteEvent(
                time=1.0,
                event_type="compute_job_complete",
                node_id=NodeId("pod-1"),
                packet=_compute_packet("p1", flops=1000.0),
            )
        )
        bus.publish(
            ComputeJobCompleteEvent(
                time=2.0,
                event_type="compute_job_complete",
                node_id=NodeId("pod-2"),
                packet=_compute_packet("p2", flops=500.0),
            )
        )
        bus.publish(
            ComputeJobCompleteEvent(
                time=3.0,
                event_type="compute_job_complete",
                node_id=NodeId("pod-1"),
                packet=_compute_packet("p3", flops=250.0),
            )
        )

        summary = collector.get_summary()
        assert summary["compute_jobs_completed"] == 3
        assert summary["compute_flops_completed"] == 1750.0
        assert summary["jobs_by_pod"] == {"pod-1": 2, "pod-2": 1}

    def test_accumulates_compute_latency(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            ComputeJobCompleteEvent(
                time=1.0,
                event_type="compute_job_complete",
                node_id=NodeId("pod-1"),
                packet=_compute_packet("p1"),
                compute_latency_s=0.25,
            )
        )
        bus.publish(
            ComputeJobCompleteEvent(
                time=2.0,
                event_type="compute_job_complete",
                node_id=NodeId("pod-1"),
                packet=_compute_packet("p2"),
                compute_latency_s=0.75,
            )
        )

        summary = collector.get_summary()
        assert summary["avg_compute_latency_s"] == pytest.approx(0.5)
        assert summary["compute_jobs_completed"] == 2

    def test_counts_compute_packet_drops(self):
        bus = EventBus()
        collector = _attach(bus)

        bus.publish(
            PacketDropEvent(
                time=1.0,
                event_type="packet_drop",
                packet=_compute_packet("p1"),
                node_id=NodeId("sat-1"),
                reason="no_route",
            )
        )
        assert collector.get_summary()["compute_drops"] == 1

    def test_ignores_non_compute_drops(self):
        bus = EventBus()
        collector = _attach(bus)

        data_packet = _compute_packet("p1")
        data_packet.flops_required = 0.0
        data_packet.packet_type = "telemetry"
        bus.publish(
            PacketDropEvent(
                time=1.0,
                event_type="packet_drop",
                packet=data_packet,
                node_id=NodeId("sat-1"),
                reason="no_route",
            )
        )
        assert collector.get_summary()["compute_drops"] == 0

    def test_flops_based_compute_drop_detection(self):
        bus = EventBus()
        collector = _attach(bus)

        packet = Packet(
            packet_id="p9",
            src=NodeId("a"),
            dst=NodeId("pod-1"),
            size_bytes=100,
            packet_type="mystery",
            created_at=0.0,
            flops_required=5000.0,
        )
        bus.publish(
            PacketDropEvent(
                time=1.0,
                event_type="packet_drop",
                packet=packet,
                node_id=NodeId("sat-1"),
                reason="no_route",
            )
        )
        assert collector.get_summary()["compute_drops"] == 1

    def test_reset_clears_tallies(self):
        bus = EventBus()
        collector = _attach(bus)
        bus.publish(
            ComputeJobCompleteEvent(
                time=1.0,
                event_type="compute_job_complete",
                node_id=NodeId("pod-1"),
                packet=_compute_packet("p1"),
            )
        )

        collector.reset()
        summary = collector.get_summary()
        assert summary["compute_jobs_completed"] == 0
        assert summary["compute_flops_completed"] == 0.0
        assert summary["jobs_by_pod"] == {}

    def test_to_dataframe(self):
        import pandas as pd

        df = ComputeMetricsCollector().to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == [
            "compute_jobs_completed",
            "compute_flops_completed",
            "compute_drops",
            "jobs_by_pod",
            "avg_compute_latency_s",
        ]
        assert len(df) == 1
