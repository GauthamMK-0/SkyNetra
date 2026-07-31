from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx

from skynetra.interface.viz.network_plots import plot_network_topology
from skynetra.interface.viz.physics_plots import plot_physics_state
from skynetra.interface.viz.scaling_plots import plot_scaling_results
from skynetra.interface.viz.topology_viz import plot_isl_connectivity


def _make_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_node("A", position=(0.0, 0.0, 0.0))
    g.add_node("B", position=(1.0, 0.0, 0.0))
    g.add_edge("A", "B", quality=0.9)
    return g


class TestNetworkPlots:
    def test_plot_network_topology_returns_figure(self):
        g = _make_graph()
        fig = plot_network_topology(g)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_network_topology_with_axes(self):
        g = _make_graph()
        fig, ax = plt.subplots()
        result = plot_network_topology(g, ax=ax)
        assert isinstance(result, plt.Figure)
        plt.close(fig)

    def test_plot_network_topology_custom_title(self):
        g = _make_graph()
        fig = plot_network_topology(g, title="Custom Title")
        assert fig.axes[0].get_title() == "Custom Title"
        plt.close(fig)


class TestTopologyViz:
    def test_plot_isl_connectivity_returns_figure(self):
        g = _make_graph()
        fig = plot_isl_connectivity(g)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_isl_connectivity_with_axes(self):
        g = _make_graph()
        fig, ax = plt.subplots()
        result = plot_isl_connectivity(g, ax=ax)
        assert isinstance(result, plt.Figure)
        plt.close(fig)

    def test_plot_isl_connectivity_empty_graph(self):
        g = nx.Graph()
        fig = plot_isl_connectivity(g)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_isl_connectivity_custom_title(self):
        g = _make_graph()
        fig = plot_isl_connectivity(g, title="ISL Viz")
        assert fig.axes[0].get_title() == "ISL Viz"
        plt.close(fig)


class TestPhysicsPlots:
    def test_plot_physics_state_returns_figure(self):
        fig = plot_physics_state({"temp": [300.0, 301.0, 302.0]})
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_physics_state_multiple_series(self):
        data = {"temp": [300.0, 301.0], "dose": [0.1, 0.2]}
        fig = plot_physics_state(data)
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_physics_state_with_axes(self):
        fig, ax = plt.subplots()
        result = plot_physics_state({"a": [1.0]}, ax=ax)
        assert isinstance(result, plt.Figure)
        plt.close(fig)

    def test_plot_physics_state_empty_series(self):
        fig = plot_physics_state({})
        assert isinstance(fig, plt.Figure)
        plt.close(fig)


class TestScalingPlots:
    def test_plot_scaling_results_returns_figure(self):
        fig = plot_scaling_results(
            configs=["small", "medium", "large"],
            metrics={"latency": [10.0, 20.0, 30.0]},
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_scaling_results_multiple_metrics(self):
        fig = plot_scaling_results(
            configs=["a", "b"],
            metrics={"cpu": [0.5, 0.8], "mem": [0.3, 0.6]},
        )
        assert isinstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_scaling_results_with_axes(self):
        fig, ax = plt.subplots()
        result = plot_scaling_results(["x"], {"y": [1.0]}, ax=ax)
        assert isinstance(result, plt.Figure)
        plt.close(fig)

    def test_plot_scaling_results_empty(self):
        fig = plot_scaling_results([], {})
        assert isinstance(fig, plt.Figure)
        plt.close(fig)
