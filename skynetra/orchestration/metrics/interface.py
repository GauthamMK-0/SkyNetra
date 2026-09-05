"""
Orchestration layer (L3) — metrics collector abstract interface.

Layer 3 interface for event-driven metrics collectors. Subscribes to
EventBus events published during the simulation loop (events defined in
`skynetra.orchestration.events`). Unlike Layer 2 engines,
MetricsCollectors are allowed to depend on Layer 3's own event types
since they live in the same layer.

Collectors accumulate tallies in `attach()` callbacks over the run and
expose them via `get_summary()` / `to_dataframe()`. `reset()` clears
the accumulated state so a collector can be reused across runs.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from skynetra.foundation.eventbus import EventBus

if TYPE_CHECKING:
    import pandas as pd


class MetricsCollector(ABC):
    """Layer 3 interface. Subscribes to EventBus events published during
    the simulation loop (events defined in skynetra.orchestration.events).
    Unlike Layer 2 engines, MetricsCollectors are allowed to depend on
    Layer 3's own event types since they live in the same layer."""

    name: str = "metrics"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    @abstractmethod
    def attach(self, event_bus: EventBus) -> None:
        """Subscribe to relevant event types."""

    @abstractmethod
    def get_summary(self) -> dict[str, Any]:
        """Accumulated metrics as a plain dict."""

    @abstractmethod
    def to_dataframe(self) -> pd.DataFrame:
        """Summary as a single-row pandas DataFrame."""

    def reset(self) -> None:
        """Clear accumulated state. Base implementation is a no-op;
        collectors override it to zero their tallies."""
