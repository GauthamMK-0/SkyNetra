"""
Domain layer (L1) — constellation configuration model.

A `ConstellationConfig` is a pure data shape: it describes the *geometry*
of a Walker-delta constellation (planes, satellites per plane, altitude,
inclination, phase offset, RAAN spread). It carries no propagation logic —
computing actual positions at a given time is the job of a propagator
(`skynetra.domain.orbit.propagator`), and choosing *which* propagator
strategy to use is a Layer 2 concern. Layer 1 defines shapes; Layer 2
defines swappable algorithms.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConstellationConfig:
    """Geometry of a Walker-delta (RAAN-spread) satellite constellation.

    Attributes:
        n_planes: Number of orbital planes `P`.
        sats_per_plane: Number of satellites per plane `S`.
        altitude_km: Circular orbital altitude above Earth's surface, km.
        inclination_deg: Orbit inclination relative to the equator, degrees.
        phase_offset_f: Walker phasing parameter `f` (int, default 1).
            The in-plane offset of plane `p` relative to plane 0 is
            `f * p * 360 / (P * S)` degrees.
        raan_spread_deg: Total right-ascension-of-ascending-node spread
            across all planes (default 360.0). Plane `p` sits at
            `p * raan_spread_deg / P`.
    """

    n_planes: int
    sats_per_plane: int
    altitude_km: float
    inclination_deg: float
    phase_offset_f: int = 1
    raan_spread_deg: float = 360.0

    @property
    def total_satellites(self) -> int:
        """Total number of satellites in the constellation."""
        return self.n_planes * self.sats_per_plane
