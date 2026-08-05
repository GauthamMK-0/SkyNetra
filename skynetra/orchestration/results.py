"""
Orchestration layer (L3) — simulation results.

`SimulationResults` is the final, serializable outcome of a run:
per-collector `engine_metrics` (one entry per metrics collector name),
the accumulated `events` published during the run, and the simulated
`duration`.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skynetra.orchestration.events import SimulationEvent


@dataclass
class SimulationResults:
    """Outcome of an `OrbitDCSimulation` run."""

    engine_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    events: list[SimulationEvent] = field(default_factory=list)
    duration: float = 0.0

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
