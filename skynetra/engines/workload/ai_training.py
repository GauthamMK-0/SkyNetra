"""
Engines layer (L2) — AI training workload generator.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import uuid
from typing import Dict, List

from skynetra.domain.packets.packet import Packet
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.engines.workload.registry import STRATEGIES
from skynetra.foundation.types import NodeId, TimeSeconds


class AITrainingWorkload(WorkloadGenerator):
    def __init__(self, profile: WorkloadProfile) -> None:
        self._profile = profile

    def generate(
        self, current_time: TimeSeconds, nodes: Dict[NodeId, object]
    ) -> List[Packet]:
        packets: List[Packet] = []
        node_ids = list(nodes.keys())
        if len(node_ids) < 2:
            return packets
        for src in node_ids:
            for dst in node_ids:
                if src != dst:
                    packets.append(
                        Packet(
                            packet_id=str(uuid.uuid4()),
                            source=src,
                            destination=dst,
                            size_bytes=self._profile.packet_size_bytes,
                            creation_time=current_time,
                            ttl=self._profile.ttl,
                            priority=self._profile.priority,
                        )
                    )
        return packets

    def name(self) -> str:
        return "ai_training"


STRATEGIES["ai_training"] = AITrainingWorkload
