"""Integration: scalability guardrails for the largest standard config.

6x10 constellation (60 satellites), 4 pods, 300s — the upper end of
what the integration suite runs — must complete comfortably inside
120s with peak Python allocations under 1 GB (tracemalloc).
"""

from __future__ import annotations

import time
import tracemalloc

from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation

COMPLETION_BUDGET_S = 120.0
MEMORY_BUDGET_BYTES = 1_000_000_000


def _large_config(strategy: str) -> FullConfig:
    return FullConfig(
        simulation={"duration_s": 300.0, "seed": 42},
        constellation={"n_planes": 6, "sats_per_plane": 10},
        pods={"n_pods": 4},
        routing={"strategy": strategy},
    )


def _run_bounded(strategy: str) -> None:
    spec = config_to_simulation_spec(_large_config(strategy))
    tracemalloc.start()
    started = time.perf_counter()
    results = OrbitDCSimulation.from_spec(spec).run()
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert elapsed < COMPLETION_BUDGET_S, f"{strategy}: took {elapsed:.1f}s"
    assert peak < MEMORY_BUDGET_BYTES, f"{strategy}: peak {peak / 1e6:.1f} MB"
    assert "network_metrics" in results.engine_metrics
    net = results.engine_metrics["network_metrics"]
    if strategy == "shortest_path":
        assert net["delivered"] > 0


def test_6x10_shortest_path_within_budget() -> None:
    _run_bounded("shortest_path")


def test_6x10_backpressure_within_budget() -> None:
    _run_bounded("backpressure")


def test_6x10_backpressure_hot_path_speed_guard() -> None:
    """Perf regression guard for the Phase 4 hot-path tables.

    The pre-optimization backpressure run took ~25s for this config;
    the cached reachability/hop tables brought it to ~1s. A 6x budget
    fails loudly if per-hop BFS work is ever reintroduced.
    """
    started = time.perf_counter()
    _run_bounded("backpressure")
    elapsed = time.perf_counter() - started
    assert elapsed < 6.0, f"backpressure hot path regressed: took {elapsed:.1f}s"
