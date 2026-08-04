"""
Engines layer (L2) — workload generator abstract interface.

Layer 2 interface for traffic generators. Layer 3 wraps `generate()` in
a SimPy process; this class itself contains no `simpy.Environment`
coupling beyond accepting `env` as a duck-typed argument (mirrors the
EventBus pattern in Layer 0) so Layer 2 stays orchestration-agnostic.

`generate()` is a generator function: it yields `env.timeout(...)`
between packet emissions and calls `publish_packet(packet)` — a
callback injected by Layer 3 rather than a direct EventBus import,
keeping this file decoupled from L0's eventbus module.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Any

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.types import NodeId


class WorkloadGenerator(ABC):
    """Layer 2 interface for traffic generators."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}

    @abstractmethod
    def generate(
        self,
        env: Any,
        publish_packet: Callable[[Packet], None],
        node_registry: dict[NodeId, Node],
    ) -> Iterator[Any]:
        """Generator function. Yields `env.timeout(...)` between packet
        emissions. Calls `publish_packet(packet)` — a callback injected
        by Layer 3 rather than a direct EventBus import.
        """
        ...

    def create_packet(
        self,
        env: Any,
        src: NodeId,
        dst: NodeId,
        size_bytes: int,
        packet_type: str,
        flops_required: float = 0.0,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Packet:
        return Packet(
            packet_id=str(uuid.uuid4()),
            src=src,
            dst=dst,
            size_bytes=size_bytes,
            packet_type=packet_type,
            created_at=env.now,
            flops_required=flops_required,
            priority=priority,
            metadata=metadata or {},
        )

    def get_active_pods(self, node_registry: dict[NodeId, Node]) -> list[NodeId]:
        return [
            nid
            for nid, n in node_registry.items()
            if isinstance(n, PodNode) and n.is_operational()
        ]
