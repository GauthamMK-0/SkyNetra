"""
Engines layer (L2) — workload subpackage.

May import from: itself, engines, domain, foundation.
"""

from skynetra.engines.workload.ai_training import AITrainingWorkload
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.engines.workload.inference import InferenceWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.engines.workload.registry import STRATEGIES, get_workload, list_workloads

__all__ = [
    "WorkloadGenerator",
    "WorkloadProfile",
    "AITrainingWorkload",
    "InferenceWorkload",
    "FederatedLearningWorkload",
    "STRATEGIES",
    "get_workload",
    "list_workloads",
]
