"""
Domain layer (L1) — node base model.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

from skynetra.foundation.types import NodeId, Vector3


@dataclass
class PhysicsState:
    position: Vector3 = (0.0, 0.0, 0.0)
    velocity: Vector3 = (0.0, 0.0, 0.0)
    temperature: float = 273.15
    radiation_dose: float = 0.0
    power_available: float = 0.0
    power_consumed: float = 0.0


@dataclass
class MetricsState:
    packets_sent: int = 0
    packets_received: int = 0
    packets_dropped: int = 0
    compute_tasks: int = 0
    compute_flops: float = 0.0
    energy_consumed: float = 0.0


class Node(ABC):
    def __init__(self, node_id: NodeId, node_type: str) -> None:
        self._node_id = node_id
        self._node_type = node_type
        self._physics = PhysicsState()
        self._metrics = MetricsState()
        self._metadata: Dict[str, Any] = {}

    @property
    def node_id(self) -> NodeId:
        return self._node_id

    @property
    def node_type(self) -> str:
        return self._node_type

    @property
    def physics(self) -> PhysicsState:
        return self._physics

    @physics.setter
    def physics(self, state: PhysicsState) -> None:
        self._physics = state

    @property
    def metrics(self) -> MetricsState:
        return self._metrics

    @abstractmethod
    def step(self, dt: float) -> None:
        ...
