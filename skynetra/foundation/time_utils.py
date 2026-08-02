"""
Foundation layer (L0) — sim-time helpers.

May import from: itself only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from skynetra.foundation.errors import ConfigError

EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)


def sim_to_wallclock(sim_time_seconds: float) -> datetime:
    return EPOCH + timedelta(seconds=sim_time_seconds)


def wallclock_to_sim(wallclock: datetime) -> float:
    return (wallclock - EPOCH).total_seconds()


def sim_time_to_orbital_phase(time_s: float, period_s: float) -> float:
    """Fractional orbital phase for a sim time, in the range [0, 1)."""
    if period_s <= 0:
        raise ConfigError("period_s must be positive")
    return (time_s % period_s) / period_s


def is_in_eclipse(
    time_s: float, period_s: float, eclipse_fraction: float
) -> bool:
    """True when the orbit phase lands inside the eclipse window."""
    if not 0.0 <= eclipse_fraction <= 1.0:
        raise ConfigError("eclipse_fraction must be within [0, 1]")
    phase = sim_time_to_orbital_phase(time_s, period_s)
    return phase < eclipse_fraction
