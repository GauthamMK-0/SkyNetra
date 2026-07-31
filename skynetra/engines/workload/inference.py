"""
Engines layer (L2) — inference workload generator.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from skynetra.domain.packets.packet import Packet
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.engines.workload.registry import STRATEGIES
from skynetra.foundation.types import NodeId, TimeSeconds


class InferenceWorkload(WorkloadGenerator):
    def __init__(
        self, profile: WorkloadProfile, ground_nodes: Optional[List[NodeId]] = None
    ) -> None:
        self._profile = profile
        self._ground_nodes = ground_nodes or []

    def generate(
        self, current_time: TimeSeconds, nodes: Dict[NodeId, object]
    ) -> List[Packet]:
        packets: List[Packet] = []
        space_nodes = [nid for nid in nodes if nid not in self._ground_nodes]
        if not space_nodes or not self._ground_nodes:
            return packets
        for gs in self._ground_nodes:
            for sn in space_nodes:
                packets.append(
                    Packet(
                        packet_id=str(uuid.uuid4()),
                        source=gs,
                        destination=sn,
                        size_bytes=self._profile.packet_size_bytes,
                        creation_time=current_time,
                        ttl=self._profile.ttl,
                        priority=self._profile.priority,
                    )
                )
        return packets

    def name(self) -> str:
        return "inference"


STRATEGIES["inference"] = InferenceWorkload
