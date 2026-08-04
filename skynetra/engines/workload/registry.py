"""
Engines layer (L2) — workload generator static registry.

Static strategy registry — NOT dynamically discovered.

Extending: add your class + import + dict entry, or instantiate a
WorkloadGenerator directly and pass it to the simulation without ever
touching this file.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

from skynetra.engines.workload.ai_training import AITrainingSyncWorkload
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.engines.workload.inference import InferenceQueryWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.foundation.errors import ConfigError

STRATEGIES: dict[str, type[WorkloadGenerator]] = {
    "ai_training_sync": AITrainingSyncWorkload,
    "inference_query": InferenceQueryWorkload,
    "federated_learning": FederatedLearningWorkload,
}


def build_workloads(specs: list[dict[str, Any]]) -> list[WorkloadGenerator]:
    """specs = [{"name": "inference_query", "config": {...}}, ...]"""
    out: list[WorkloadGenerator] = []
    for spec in specs:
        cls = STRATEGIES.get(spec["name"])
        if cls is None:
            raise ConfigError(f"Unknown workload '{spec['name']}'")
        out.append(cls(spec.get("config", {})))
    return out
