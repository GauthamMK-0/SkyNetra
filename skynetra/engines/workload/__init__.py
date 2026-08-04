"""
Engines layer (L2) — workload subpackage.

May import from: itself, engines, domain, foundation.
"""

from skynetra.engines.workload.ai_training import AITrainingSyncWorkload
from skynetra.engines.workload.federated_learning import FederatedLearningWorkload
from skynetra.engines.workload.inference import InferenceQueryWorkload
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import (
    AITrainingSyncProfile,
    FederatedLearningProfile,
    ImageryDownlinkProfile,
    InferenceQueryProfile,
)
from skynetra.engines.workload.registry import STRATEGIES, build_workloads

__all__ = [
    "WorkloadGenerator",
    "AITrainingSyncProfile",
    "InferenceQueryProfile",
    "FederatedLearningProfile",
    "ImageryDownlinkProfile",
    "AITrainingSyncWorkload",
    "InferenceQueryWorkload",
    "FederatedLearningWorkload",
    "STRATEGIES",
    "build_workloads",
]
