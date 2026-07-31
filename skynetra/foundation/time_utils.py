"""
Foundation layer (L0) — sim-time <-> wallclock helpers.

May import from: itself only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)


def sim_to_wallclock(sim_time_seconds: float) -> datetime:
    return EPOCH + timedelta(seconds=sim_time_seconds)


def wallclock_to_sim(wallclock: datetime) -> float:
    return (wallclock - EPOCH).total_seconds()
