"""
Orchestration layer (L3) — simulation results.

`SimulationResults` is the final, serializable outcome of a run:
per-collector `engine_metrics` (one entry per metrics collector name),
the accumulated `events` published during the run, and the simulated
`duration`.

Provides typed summary accessors (network, compute, physics, topology),
dashboard reporting (.report()), and visualization export (.plot()).

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from skynetra.orchestration.events import SimulationEvent


@dataclass(frozen=True)
class NetworkSummary:
    """Convenience accessor for network performance metrics."""

    transmitted: int = 0
    delivered: int = 0
    dropped: int = 0
    avg_latency_s: float = 0.0
    drop_rate: float = 0.0
    throughput_gbps: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.avg_latency_s * 1000.0

    @property
    def delivery_rate(self) -> float:
        total = self.delivered + self.dropped
        return (self.delivered / total * 100.0) if total > 0 else 100.0


@dataclass(frozen=True)
class ComputeSummary:
    """Convenience accessor for on-orbit accelerator compute metrics."""

    jobs_completed: int = 0
    total_flops: float = 0.0
    compute_drops: int = 0
    avg_service_time_s: float = 0.0
    jobs_by_pod: dict[str, int] = field(default_factory=dict)

    @property
    def avg_service_time_ms(self) -> float:
        return self.avg_service_time_s * 1000.0


@dataclass(frozen=True)
class PhysicsSummary:
    """Convenience accessor for space environment physics dynamics."""

    thermal_throttle_events: int = 0
    radiation_fault_events: int = 0
    physics_caused_drops: int = 0
    avg_temperature_k: float = 0.0
    total_energy_j: float = 0.0
    active_models: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TopologySummary:
    """Convenience accessor for constellation graph topology dynamics."""

    node_count: int = 0
    edge_count: int = 0
    topology_updates: int = 0


@dataclass
class SimulationResults:
    """Outcome of an `OrbitDCSimulation` run with rich reporting and telemetry."""

    engine_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[SimulationEvent] = field(default_factory=list)
    duration: float = 0.0

    @property
    def network(self) -> NetworkSummary:
        """Typed network metrics summary."""
        raw = self.engine_metrics.get("network_metrics", {})
        return NetworkSummary(
            transmitted=int(raw.get("transmitted", 0)),
            delivered=int(raw.get("delivered", 0)),
            dropped=int(raw.get("dropped", 0)),
            avg_latency_s=float(raw.get("avg_latency_s", 0.0)),
            drop_rate=float(raw.get("drop_rate", 0.0)),
            throughput_gbps=float(raw.get("throughput_gbps", 0.0)),
        )

    @property
    def compute(self) -> ComputeSummary:
        """Typed on-orbit compute metrics summary."""
        raw = self.engine_metrics.get("compute_metrics", {})
        return ComputeSummary(
            jobs_completed=int(raw.get("compute_jobs_completed", 0)),
            total_flops=float(raw.get("compute_flops_completed", 0.0)),
            compute_drops=int(raw.get("compute_drops", 0)),
            avg_service_time_s=float(raw.get("avg_compute_latency_s", 0.0)),
            jobs_by_pod=dict(raw.get("jobs_by_pod", {})),
        )

    @property
    def physics(self) -> PhysicsSummary:
        """Typed space physics metrics summary."""
        raw = self.engine_metrics.get("physics_metrics", {})
        return PhysicsSummary(
            thermal_throttle_events=int(raw.get("thermal_throttle_events", 0)),
            radiation_fault_events=int(raw.get("radiation_fault_events", 0)),
            physics_caused_drops=int(raw.get("physics_caused_drops", 0)),
            avg_temperature_k=float(raw.get("avg_temperature", 0.0)),
            total_energy_j=float(raw.get("total_energy_consumed", 0.0)),
            active_models=list(raw.get("active_models", [])),
        )

    @property
    def topology(self) -> TopologySummary:
        """Typed topology graph metrics summary."""
        raw = self.engine_metrics.get("topology_metrics", {})
        return TopologySummary(
            node_count=int(raw.get("final_node_count", 0)),
            edge_count=int(raw.get("final_edge_count", 0)),
            topology_updates=int(raw.get("topology_updates", 0)),
        )

    def report(self, title: str = "SKYNETRA SIMULATION EXECUTION REPORT") -> str:
        """Format and print a detailed multi-section terminal dashboard report.

        Returns the formatted string for logging or inspection.
        """
        lines: list[str] = []
        divider = "=" * 70
        lines.append("\n" + divider)
        lines.append(f"{title:^70}")
        lines.append(divider)
        lines.append(f"Simulation Horizon : {self.duration:.1f} simulated seconds")

        # Network section
        net = self.network
        lines.append("\n[Network Forwarding & Delivery]")
        lines.append(f"  * Packets Injected/Transmitted : {net.transmitted} packets")
        lines.append(f"  * Successfully Received/Relayed: {net.delivered} packets")
        lines.append(f"  * Packets Dropped (Congestion) : {net.dropped} packets")
        lines.append(f"  * Mean End-to-End Latency      : {net.avg_latency_ms:.2f} ms")
        lines.append(f"  * Packet Loss Rate             : {net.drop_rate * 100:.2f}%")
        lines.append(f"  * Delivery Completion Rate     : {net.delivery_rate:.2f}%")

        # Compute section
        comp = self.compute
        lines.append("\n[On-Orbit Compute Data Center Servicing]")
        lines.append(f"  * Compute Tasks Finished       : {comp.jobs_completed} jobs")
        lines.append(f"  * Total FLOPs Accrued          : {comp.total_flops:.2e} FLOPS")
        lines.append(f"  * Mean Compute Service Time    : {comp.avg_service_time_ms:.2f} ms")
        if comp.jobs_by_pod:
            lines.append("  * Per-Pod Task Distribution    :")
            for pod_id, count in sorted(comp.jobs_by_pod.items()):
                pct = (count / max(1, net.delivered)) * 100
                lines.append(f"      - {pod_id:<8} : {count:>3} jobs ({pct:>5.1f}%)")

        # Physics section
        phys = self.physics
        lines.append("\n[Space Environment & Physics Models]")
        models_str = str(phys.active_models) if phys.active_models else "None"
        lines.append(f"  * Active Physics Models        : {models_str}")
        lines.append(f"  * Mean Radiative Core Temp     : {phys.avg_temperature_k:.1f} K")
        lines.append(f"  * Thermal Throttle Incidents   : {phys.thermal_throttle_events}")
        lines.append(f"  * Radiation Latchup Faults     : {phys.radiation_fault_events}")
        lines.append(f"  * Total Energy Consumed        : {phys.total_energy_j:.2f} Joules")

        # Topology section
        top = self.topology
        lines.append("\n[Constellation Topology & Mesh Evolution]")
        lines.append(f"  * Constellation Vertices       : {top.node_count} nodes")
        lines.append(f"  * Active Intersatellite Links  : {top.edge_count} links")
        lines.append(f"  * Topology Recomputations      : {top.topology_updates} updates")
        lines.append(divider)

        report_text = "\n".join(lines)
        print(report_text)
        return report_text

    # Injected by Layer 4 (skynetra.interface.reporting) without upward imports
    _plotter: ClassVar[Callable[..., list[Path]] | None] = None

    @classmethod
    def register_plotter(
        cls, plotter: Callable[..., list[Path]]
    ) -> None:
        """Register the Layer 4 plotting implementation via dependency injection."""
        cls._plotter = plotter

    def plot(self, output_dir: str | Path = "results/plots") -> list[Path]:
        """Generate and save all visualization figures directly from results.

        Requires `skynetra.interface` (or top-level `skynetra`) to be imported.
        """
        plotter = SimulationResults._plotter
        if plotter is None:
            raise RuntimeError(
                "Plotting requires the interface visualization engine. "
                "Ensure skynetra.interface is loaded (e.g. import skynetra)."
            )
        return plotter(self, str(output_dir))

    def to_dict(self) -> dict[str, Any]:
        """Plain, JSON-friendly representation of the results."""
        return {
            "engine_metrics": self.engine_metrics,
            "events": [
                {
                    "time": getattr(ev, "time", None),
                    "event_type": ev.event_type,
                }
                for ev in self.events
            ],
            "duration": self.duration,
        }

    def compare(self, other: SimulationResults) -> dict[str, Any]:
        """Compare with another result set; returns per-key diff summary."""
        diffs: dict[str, Any] = {}
        if self.duration != other.duration:
            diffs["duration"] = {"self": self.duration, "other": other.duration}
        metric_names = set(self.engine_metrics) | set(other.engine_metrics)
        for name in sorted(metric_names):
            mine = self.engine_metrics.get(name)
            theirs = other.engine_metrics.get(name)
            if mine != theirs:
                diffs[f"engine_metrics.{name}"] = {"self": mine, "other": theirs}
        return diffs
