"""
Engines layer (L2) — inference query workload generator.

Query traffic toward compute pods, with three arrival patterns:

  poisson  — exponentially distributed inter-arrival times with mean
             `mean_interval_s` (the standard Poisson process).
  on_off   — queries at the poisson rate during `on_duration_s`
             windows, then silence for `off_duration_s`.
  bursty   — `burst_size` queries spaced `burst_interval_s` apart,
             then silence for `burst_idle_s`.

Query sources come from `sources` (fallback: every node in the
registry); destinations are drawn from the operational pods. With no
operational pods nothing is emitted. Inter-arrivals are driven by a
seeded `random.Random`, so `seed` reproduces the identical sequence.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from typing import Any

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import (
    ARRIVAL_BURSTY,
    ARRIVAL_ON_OFF,
    ARRIVAL_POISSON,
    InferenceQueryProfile,
)
from skynetra.foundation.errors import ConfigError
from skynetra.foundation.types import NodeId


class InferenceQueryWorkload(WorkloadGenerator):
    """Poisson / on-off / bursty query arrivals toward compute pods."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        fields = InferenceQueryProfile.__dataclass_fields__
        profile_config = {k: v for k, v in self._config.items() if k in fields}
        self._profile = InferenceQueryProfile(**profile_config)
        if self._profile.arrival_pattern not in (
            ARRIVAL_POISSON,
            ARRIVAL_ON_OFF,
            ARRIVAL_BURSTY,
        ):
            raise ConfigError(
                f"Unknown arrival pattern '{self._profile.arrival_pattern}'. "
                f"Available: {[ARRIVAL_POISSON, ARRIVAL_ON_OFF, ARRIVAL_BURSTY]}"
            )
        self._rng = random.Random(self._profile.seed)

    @property
    def profile(self) -> InferenceQueryProfile:
        return self._profile

    def _emit_query(
        self,
        env: Any,
        publish_packet: Callable[[Packet], None],
        sources: list[NodeId],
        pods: list[NodeId],
    ) -> None:
        publish_packet(
            self.create_packet(
                env,
                self._rng.choice(sources),
                self._rng.choice(pods),
                self._profile.query_size_bytes,
                self._profile.packet_type,
                priority=self._profile.priority,
            )
        )

    def generate(
        self,
        env: Any,
        publish_packet: Callable[[Packet], None],
        node_registry: dict[NodeId, Node],
    ) -> Iterator[Any]:
        pods = self.get_active_pods(node_registry)
        if not pods:
            return
        sources = [nid for nid in self._profile.sources if nid in node_registry]
        if not sources:
            sources = list(node_registry.keys())
        profile = self._profile
        pattern = profile.arrival_pattern
        if pattern == ARRIVAL_POISSON:
            while True:
                yield env.timeout(self._rng.expovariate(1.0 / profile.mean_interval_s))
                self._emit_query(env, publish_packet, sources, pods)
        elif pattern == ARRIVAL_ON_OFF:
            while True:
                on_end = env.now + profile.on_duration_s
                while env.now < on_end:
                    yield env.timeout(
                        self._rng.expovariate(1.0 / profile.mean_interval_s)
                    )
                    if env.now >= on_end:
                        break
                    self._emit_query(env, publish_packet, sources, pods)
                yield env.timeout(profile.off_duration_s)
        else:  # ARRIVAL_BURSTY
            while True:
                for _ in range(profile.burst_size):
                    self._emit_query(env, publish_packet, sources, pods)
                    yield env.timeout(profile.burst_interval_s)
                yield env.timeout(profile.burst_idle_s)
