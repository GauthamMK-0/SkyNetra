"""
Domain layer (L1) — propagator contract and reference implementation.

Why are there two propagator homes?

This layer defines the *contract* (`PropagatorInterface`) plus exactly one
trivial, dependency-free reference implementation
(`ReferenceCircularPropagator`). That reference lives here because it is
domain-model-adjacent: it exists so Layer 1 tests and topology builders can
produce satellite positions without pulling in Layer 2 or any optional
heavy dependency (skyfield, sgp4, ...).

The full swappable propagator *strategy family* — Walker-delta variants,
SGP4-based propagation, J2-perturbed models, and so on — is intentionally a
Layer 2 (`skynetra.engines`) concern. Those are interchangeable *algorithms*
chosen at runtime through a strategy registry, and several require optional
heavy third-party dependencies (skyfield, sgp4) that Layer 1 must not
import.

This mirrors the routing/physics/workload split across the whole project:
Layer 1 defines the shapes (data models, ABCs, schema slots), Layer 2
defines the swappable algorithms that populate them. A consumer should
depend on `PropagatorInterface`; it should never import a concrete
propagator class from Layer 1 except the reference one, and never from a
hardcoded location when runtime strategy selection matters.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.foundation.math_utils import kepler_period_s, orbital_elements_to_eci
from skynetra.foundation.types import NodeId, Vector3


class PropagatorInterface(ABC):
    """Layer 1 interface only — no concrete high-fidelity implementations
    live here. Layer 2 is where alternate propagator STRATEGIES that
    need extra dependencies (SGP4/skyfield) are registered, because they
    are 'engines' with swappable behavior. This file defines only the
    contract plus one trivial reference implementation used by tests.
    """

    @abstractmethod
    def get_positions(
        self, time_s: float, constellation: ConstellationConfig
    ) -> dict[NodeId, Vector3]:
        """Return ECI positions (km) for every satellite at `time_s`.

        The mapping must be consistent with `get_sat_ids`: every id
        returned there appears as a key here, with no extras.
        """
        ...

    @abstractmethod
    def get_sat_ids(
        self, constellation: ConstellationConfig
    ) -> list[NodeId]:
        """Return the deterministic, ordered list of satellite ids."""
        ...

    def get_orbital_period_s(self, altitude_km: float) -> float:
        """Kepler orbital period (s) for a circular orbit at `altitude_km`."""
        return kepler_period_s(altitude_km)


class ReferenceCircularPropagator(PropagatorInterface):
    """Minimal Walker-delta circular propagator, dependency-free.

    This is the ONLY concrete propagator implemented at Layer 1;
    it exists so Layer 1 domain tests do not need Layer 2.
    The full swappable propagator strategy set (including SGP4-based)
    lives in `skynetra.engines` (Layer 2) as it requires optional heavy
    dependencies and represents an interchangeable *algorithm*, not a
    fixed data model.

    Walker-delta geometry (standard phasing):
      * Plane `p` (0-based) has RAAN `p * raan_spread_deg / n_planes`.
      * Satellite `s` (0-based) in plane `p` starts at in-plane angle
        `s * 360 / sats_per_plane + phase_offset_f * p * 360 / (n_planes * sats_per_plane)`
        degrees past the ascending node.
      * All orbits are circular; the in-plane angle advances uniformly at
        mean motion `360 / period` degrees per second.
    """

    def get_positions(
        self, time_s: float, constellation: ConstellationConfig
    ) -> dict[NodeId, Vector3]:
        period = self.get_orbital_period_s(constellation.altitude_km)
        mean_motion_deg_s = 360.0 / period
        plane_count = constellation.n_planes
        sats_per_plane = constellation.sats_per_plane

        positions: dict[NodeId, Vector3] = {}
        for plane in range(plane_count):
            raan_deg = plane * constellation.raan_spread_deg / plane_count
            for sat in range(sats_per_plane):
                phase_offset_deg = (
                    constellation.phase_offset_f
                    * plane
                    * 360.0
                    / (plane_count * sats_per_plane)
                )
                mean_anomaly_deg = (
                    sat * 360.0 / sats_per_plane
                    + phase_offset_deg
                    + time_s * mean_motion_deg_s
                )
                positions[self._sat_id(plane, sat)] = orbital_elements_to_eci(
                    inc_deg=constellation.inclination_deg,
                    raan_deg=raan_deg,
                    mean_anomaly_deg=mean_anomaly_deg,
                    altitude_km=constellation.altitude_km,
                )
        return positions

    def get_sat_ids(
        self, constellation: ConstellationConfig
    ) -> list[NodeId]:
        return [
            self._sat_id(plane, sat)
            for plane in range(constellation.n_planes)
            for sat in range(constellation.sats_per_plane)
        ]

    @staticmethod
    def _sat_id(plane: int, sat: int) -> NodeId:
        return NodeId(f"sat-{plane}-{sat}")
