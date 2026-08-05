"""Layer 4 viz + reporting tests: figures, fallbacks, exports."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId
from skynetra.interface.reporting import (
    export_results_csv,
    export_results_json,
    print_comparison_table,
    save_all_plots,
)
from skynetra.interface.viz.network_plots import (
    latency_cdf_plot,
    link_utilization_heatmap,
    throughput_plot,
)
from skynetra.interface.viz.physics_plots import (
    NO_PHYSICS_MESSAGE,
    physics_vs_network_impact,
    power_state_timeseries,
    radiation_dose_accumulation,
    temperature_timeseries,
)
from skynetra.interface.viz.scaling_plots import (
    drop_rate_vs_load,
    latency_vs_constellation_size,
    physics_impact_vs_scale,
    throughput_vs_num_pods,
)
from skynetra.interface.viz.topology_viz import plot_orbit_and_isl
from skynetra.orchestration.events import (
    PacketDeliveredEvent,
    PacketTransmitEvent,
    PhysicsTickEvent,
)
from skynetra.orchestration.results import SimulationResults


def _packet(pid: str, src: str, dst: str) -> Packet:
    return Packet(
        packet_id=pid,
        src=NodeId(src),
        dst=NodeId(dst),
        size_bytes=1000,
        packet_type="inference_query",
        created_at=0.0,
    )


def _make_results(with_physics: bool = True) -> SimulationResults:
    events = [
        PacketTransmitEvent(
            time=1.0,
            event_type="packet_transmit",
            packet=_packet("p1", "pod-1", "gs-1"),
            node_id=NodeId("sat-0-0"),
            to_node=NodeId("sat-0-1"),
        ),
        PacketTransmitEvent(
            time=2.0,
            event_type="packet_transmit",
            packet=_packet("p2", "pod-1", "gs-1"),
            node_id=NodeId("sat-0-1"),
            to_node=NodeId("gs-1"),
        ),
        PacketDeliveredEvent(
            time=2.5,
            event_type="packet_delivered",
            packet=_packet("p1", "pod-1", "gs-1"),
            node_id=NodeId("gs-1"),
            latency_s=1.5,
        ),
        PacketDeliveredEvent(
            time=3.0,
            event_type="packet_delivered",
            packet=_packet("p2", "pod-1", "gs-1"),
            node_id=NodeId("gs-1"),
            latency_s=1.0,
        ),
    ]
    if with_physics:
        events.append(
            PhysicsTickEvent(
                time=1.0,
                event_type="physics_tick",
                tick=1,
                node_state={
                    NodeId("sat-0-0"): {
                        "physics_state": {
                            "temperature_k": 310.0,
                            "radiation_dose_rad": 0.5,
                            "battery_charge_wh": 480.0,
                            "power_available_w": 2900.0,
                        },
                        "metrics_state": {},
                    },
                    NodeId("sat-0-1"): {
                        "physics_state": {
                            "temperature_k": 315.0,
                            "radiation_dose_rad": 1.0,
                            "battery_charge_wh": 470.0,
                            "power_available_w": 2800.0,
                        },
                        "metrics_state": {},
                    },
                },
                active_models=["ThermalModel", "RadiationModel", "PowerModel"],
            )
        )
    engine_metrics = {
        "network_metrics": {
            "delivered": 2,
            "dropped": 1,
            "transmitted": 5,
            "avg_latency_s": 1.25,
            "drop_rate": 0.2,
        },
        "topology_metrics": {"final_node_count": 4, "final_edge_count": 3},
    }
    if with_physics:
        engine_metrics["physics_metrics"] = {
            "thermal_throttle_events": 0,
            "radiation_fault_events": 0,
            "physics_caused_drops": 1,
            "avg_temperature": 312.5,
            "total_energy_consumed": 100.0,
            "active_models": ["ThermalModel", "RadiationModel", "PowerModel"],
        }
    return SimulationResults(
        engine_metrics=engine_metrics,
        events=events,
        duration=60.0,
    )


NETWORK_PLOTS = [latency_cdf_plot, throughput_plot, link_utilization_heatmap]
PHYSICS_PLOTS = [
    temperature_timeseries,
    radiation_dose_accumulation,
    power_state_timeseries,
    physics_vs_network_impact,
]
SCALING_PLOTS = [
    latency_vs_constellation_size,
    throughput_vs_num_pods,
    drop_rate_vs_load,
    physics_impact_vs_scale,
]


class TestNetworkPlots:
    @pytest.mark.parametrize("plot_fn", NETWORK_PLOTS)
    def test_returns_figure(self, plot_fn) -> None:
        fig = plot_fn(_make_results())
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    @pytest.mark.parametrize("plot_fn", NETWORK_PLOTS)
    def test_empty_events_fallback(self, plot_fn) -> None:
        results = SimulationResults(engine_metrics={}, events=[], duration=60.0)
        fig = plot_fn(results)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_latency_cdf_uses_delivered_latencies(self) -> None:
        fig = latency_cdf_plot(_make_results())
        assert len(fig.axes[0].lines) == 1
        plt.close(fig)

    def test_throughput_bins_by_second(self) -> None:
        fig = throughput_plot(_make_results())
        line = fig.axes[0].lines[0]
        assert max(line.get_ydata()) == 1  # one transmit in second 1, one in second 2
        plt.close(fig)

    def test_heatmap_counts_directed_links(self) -> None:
        fig = link_utilization_heatmap(_make_results())
        ax = fig.axes[0]
        assert ax.images[0].get_array().max() == 1
        plt.close(fig)


class TestScalingPlots:
    @pytest.mark.parametrize("plot_fn", SCALING_PLOTS)
    def test_returns_figure(self, plot_fn) -> None:
        fig = plot_fn([_make_results(), _make_results()])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    @pytest.mark.parametrize("plot_fn", SCALING_PLOTS)
    def test_empty_list_fallback(self, plot_fn) -> None:
        fig = plot_fn([])
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_physics_impact_excludes_non_physics_runs(self) -> None:
        results = [_make_results(with_physics=False), _make_results(with_physics=True)]
        fig = physics_impact_vs_scale(results)
        assert len(fig.axes[0].lines[0].get_xdata()) == 1
        plt.close(fig)


class TestTopologyViz:
    def test_returns_figure(self) -> None:
        snapshot = {
            "positions": {
                "sat-0-0": (0.0, 0.0, 550.0),
                "sat-0-1": (100.0, 0.0, 550.0),
                "sat-0-2": (200.0, 50.0, 550.0),
            },
            "edges": [("sat-0-0", "sat-0-1"), ("sat-0-1", "sat-0-2")],
            "title": "Test topology",
        }
        fig = plot_orbit_and_isl(snapshot)
        assert isinstance(fig, plt.Figure)
        assert fig.axes[0].get_title() == "Test topology"
        plt.close(fig)

    def test_empty_snapshot_fallback(self) -> None:
        fig = plot_orbit_and_isl({})
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestPhysicsPlots:
    @pytest.mark.parametrize("plot_fn", PHYSICS_PLOTS)
    def test_returns_figure_with_physics_data(self, plot_fn) -> None:
        fig = plot_fn(_make_results(with_physics=True))
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    @pytest.mark.parametrize("plot_fn", PHYSICS_PLOTS)
    def test_fallback_without_physics_metrics(self, plot_fn) -> None:
        fig = plot_fn(_make_results(with_physics=False))
        assert isinstance(fig, plt.Figure)
        texts = [t.get_text() for t in fig.axes[0].texts]
        assert any(NO_PHYSICS_MESSAGE in text for text in texts)
        plt.close(fig)


class TestReporting:
    def test_export_results_csv(self, tmp_path: Path) -> None:
        path = str(tmp_path / "out.csv")
        export_results_csv(_make_results(), path)
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        assert rows[0][0] == "collector"
        assert "network_metrics" in {row[0] for row in rows[1:]}
        net_row = next(row for row in rows[1:] if row[0] == "network_metrics")
        assert "delivered" in rows[0]
        assert "2" in net_row

    def test_export_results_json(self, tmp_path: Path) -> None:
        path = str(tmp_path / "out.json")
        export_results_json(_make_results(), path)
        raw = json.loads(Path(path).read_text())
        assert raw["duration"] == 60.0
        assert raw["engine_metrics"]["network_metrics"]["delivered"] == 2

    def test_print_comparison_table(self, capsys: pytest.CaptureFixture) -> None:
        a = _make_results()
        b = _make_results()
        b.engine_metrics["network_metrics"]["delivered"] = 5
        print_comparison_table(a, b)
        out = capsys.readouterr().out
        assert "collector" in out
        assert "delivered" in out
        assert "network_metrics" in out

    def test_save_all_plots(self, tmp_path: Path) -> None:
        save_all_plots(_make_results(), str(tmp_path))
        expected = {
            "latency_cdf_plot",
            "throughput_plot",
            "link_utilization_heatmap",
            "temperature_timeseries",
            "radiation_dose_accumulation",
            "power_state_timeseries",
            "physics_vs_network_impact",
        }
        saved = {p.stem for p in tmp_path.glob("*.png")}
        assert saved == expected
