"""
Domain layer (L1) — packet data model.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from skynetra.foundation.types import NodeId, TimeSeconds


@dataclass
class Packet:
    packet_id: str
    source: NodeId
    destination: NodeId
    size_bytes: int
    creation_time: TimeSeconds
    payload: Optional[Dict[str, Any]] = None
    ttl: int = 64
    priority: int = 0
    path: list[str] = field(default_factory=list)
    hops: int = 0
    arrived: bool = False
