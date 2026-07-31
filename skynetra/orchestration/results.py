"""
Orchestration layer (L3) — simulation results.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SimulationResults:
    metrics: Dict[str, Any] = field(default_factory=dict)
    events: List[Any] = field(default_factory=list)
    duration: float = 0.0
