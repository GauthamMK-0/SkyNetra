"""
Engines layer (L2) — workload profile dataclasses.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class WorkloadProfile:
    name: str
    packet_size_bytes: int = 1024
    generation_rate: float = 1.0
    priority: int = 0
    ttl: int = 64
    payload_schema: Dict[str, str] = field(default_factory=dict)
