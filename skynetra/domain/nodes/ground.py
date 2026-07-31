"""
Domain layer (L1) — ground station node.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from skynetra.domain.nodes.base import Node
from skynetra.foundation.types import NodeId


class GroundStation(Node):
    def __init__(
        self,
        node_id: NodeId,
        latitude: float = 0.0,
        longitude: float = 0.0,
        altitude_m: float = 0.0,
    ) -> None:
        super().__init__(node_id, node_type="ground")
        self._latitude = latitude
        self._longitude = longitude
        self._altitude_m = altitude_m

    @property
    def latitude(self) -> float:
        return self._latitude

    @property
    def longitude(self) -> float:
        return self._longitude

    @property
    def altitude_m(self) -> float:
        return self._altitude_m

    def step(self, dt: float) -> None:
        pass
