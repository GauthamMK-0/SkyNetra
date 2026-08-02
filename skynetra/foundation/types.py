"""
Foundation layer (L0) — type aliases.

Any layer may import these types. They carry no behavior.

May import from: itself only.
"""

from __future__ import annotations

from typing import NewType

NodeId = NewType("NodeId", str)
LinkId = NewType("LinkId", str)  # canonical form "{node_a}->{node_b}"
TimeSeconds = NewType("TimeSeconds", float)
Vector3 = tuple[float, float, float]


__all__ = [
    "NodeId",
    "LinkId",
    "TimeSeconds",
    "Vector3",
]
