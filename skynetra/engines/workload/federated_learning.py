"""
Engines layer (L2) — federated learning workload generator.

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


class FederatedLearningWorkload(WorkloadGenerator):
    def __init__(self, profile: WorkloadProfile, aggregator: NodeId) -> None:
        self._profile = profile
        self._aggregator = aggregator

    def generate(
        self, current_time: TimeSeconds, nodes: Dict[NodeId, object]
    ) -> List[Packet]:
        packets = []
        for nid in nodes:
            if nid != self._aggregator:
                packets.append(
                    Packet(
                        packet_id=str(uuid.uuid4()),
                        source=nid,
                        destination=self._aggregator,
                        size_bytes=self._profile.packet_size_bytes,
                        creation_time=current_time,
                        ttl=self._profile.ttl,
                        priority=self._profile.priority,
                    )
                )
        return packets

    def name(self) -> str:
        return "federated_learning"


STRATEGIES["federated_learning"] = FederatedLearningWorkload
