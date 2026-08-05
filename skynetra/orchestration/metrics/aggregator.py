"""
Orchestration layer (L3) — metrics aggregator.

Composes a list of MetricsCollector instances, wiring each to the shared
EventBus once during `OrbitDCSimulation.setup()`. Collectors accumulate
throughout the run; `get_all_summaries()` / `get_combined_summary()`
expose the final tallies, `export_all()` writes them to disk, and
`compare()` diffs against another aggregator's summaries.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skynetra.foundation.eventbus import EventBus
from skynetra.orchestration.metrics.interface import MetricsCollector


class MetricsAggregator:
    """Composes a list of MetricsCollector instances, wires each to the
    shared EventBus once during OrbitDCSimulation.setup()."""

    def __init__(self, collectors: list[MetricsCollector], event_bus: EventBus) -> None:
        self.collectors = list(collectors)
        for collector in self.collectors:
            collector.attach(event_bus)

    def get_all_summaries(self) -> dict[str, dict[str, Any]]:
        """Per-collector summaries keyed by collector name."""
        return {collector.name: collector.get_summary() for collector in self.collectors}

    def get_combined_summary(self) -> dict[str, Any]:
        """Flat summary with dotted `name.metric` keys (lossless merge)."""
        combined: dict[str, Any] = {}
        for collector in self.collectors:
            for metric, value in collector.get_summary().items():
                combined[f"{collector.name}.{metric}"] = value
        return combined

    def export_all(self, output_dir: str) -> None:
        """Write one `<collector_name>.csv` per collector into `output_dir`."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        for collector in self.collectors:
            collector.to_dataframe().to_csv(path / f"{collector.name}.csv", index=False)

    def compare(self, other: MetricsAggregator) -> dict[str, Any]:
        """Per-collector, per-numeric-key deltas and pct changes vs `other`.

        Returns::

            {collector_name: {metric: {"delta": a - b,
                                       "pct_change": delta / b * 100}}}
        """
        diffs: dict[str, Any] = {}
        names = {c.name for c in self.collectors} | {c.name for c in other.collectors}
        mine = self.get_all_summaries()
        theirs = other.get_all_summaries()
        for name in sorted(names):
            a = mine.get(name) or {}
            b = theirs.get(name) or {}
            metric_diffs: dict[str, Any] = {}
            for metric in sorted(set(a) | set(b)):
                value_a = a.get(metric)
                value_b = b.get(metric)
                if isinstance(value_a, (int, float)):
                    value_a_num = float(value_a)
                elif value_a is None:
                    value_a_num = 0.0
                else:
                    continue
                if isinstance(value_b, (int, float)):
                    value_b_num = float(value_b)
                elif value_b is None:
                    value_b_num = 0.0
                else:
                    continue
                if value_a_num == value_b_num:
                    continue
                delta = value_a_num - value_b_num
                pct_change = delta / value_b_num * 100.0 if value_b_num else None
                metric_diffs[metric] = {"delta": delta, "pct_change": pct_change}
            if metric_diffs:
                diffs[name] = metric_diffs
        return diffs

    def reset_all(self) -> None:
        """Reset every collector's accumulated state."""
        for collector in self.collectors:
            collector.reset()
