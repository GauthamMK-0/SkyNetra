"""
Engines layer (L2) — static workload generator registry.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Dict, Type

from skynetra.engines.workload.interface import WorkloadGenerator

STRATEGIES: Dict[str, Type[WorkloadGenerator]] = {}


def get_workload(name: str, **kwargs: object) -> WorkloadGenerator:
    cls = STRATEGIES.get(name)
    if cls is None:
        raise KeyError(f"Unknown workload generator: {name}")
    return cls(**kwargs)


def list_workloads() -> list[str]:
    return list(STRATEGIES.keys())
