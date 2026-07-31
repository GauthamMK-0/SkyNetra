"""
Domain layer (L1) — constellation configuration model.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConstellationConfig:
    name: str
    num_planes: int
    satellites_per_plane: int
    inclination: float
    altitude_km: float
    eccentricity: float = 0.0
    arg_of_perigee: float = 0.0
    raan_spacing: str = "even"
    true_anomaly_spacing: str = "even"
    epoch: Optional[str] = None
    additional_params: dict[str, object] = field(default_factory=dict)

    @property
    def total_satellites(self) -> int:
        return self.num_planes * self.satellites_per_plane
