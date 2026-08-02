"""
Domain layer (L1) — packet data model.

A packet is the unit of work flowing through the network: data payloads
between nodes, and compute tasks toward pods (the `flops_required` slot).
It carries routing bookkeeping (`hops`, `path_history`, `priority`) as
pure data — the algorithms that read and write these fields live in
Layer 2 (routing engines) and Layer 3 (simulation loop).

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from skynetra.foundation.types import NodeId


@dataclass
class Packet:
    packet_id: str
    src: NodeId
    dst: NodeId
    size_bytes: int
    packet_type: str
    created_at: float
    flops_required: float = 0.0
    priority: int = 0
    hops: int = 0
    path_history: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
