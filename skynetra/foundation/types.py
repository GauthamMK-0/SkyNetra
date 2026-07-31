"""
Foundation layer (L0) — type aliases.

May import from: itself only.
"""

from __future__ import annotations

from typing import NewType, Tuple

NodeId = NewType("NodeId", str)
LinkId = NewType("LinkId", str)
TimeSeconds = NewType("TimeSeconds", float)
Vector3 = Tuple[float, float, float]
