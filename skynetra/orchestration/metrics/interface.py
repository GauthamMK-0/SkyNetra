"""
Orchestration layer (L3) — metrics collector abstract interface.

May import from: itself, orchestration, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from skynetra.orchestration.context import SimulationContext


class MetricsCollector(ABC):
    @abstractmethod
    def collect(self, context: SimulationContext) -> Dict[str, Any]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
