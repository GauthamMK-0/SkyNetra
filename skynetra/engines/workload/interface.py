"""
Engines layer (L2) — workload generator abstract interface.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId, TimeSeconds


class WorkloadGenerator(ABC):
    @abstractmethod
    def generate(
        self, current_time: TimeSeconds, nodes: Dict[NodeId, object]
    ) -> List[Packet]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
