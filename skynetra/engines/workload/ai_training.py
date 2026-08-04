"""
Engines layer (L2) — AI training sync workload generator.

Distributed training gradient-sync traffic, in rounds:

  all_reduce        — every worker sends its gradient to every other
                       worker: N*(N-1) packets per round.
  parameter_server  — every worker sends to the first active pod
                       (server): N-1 packets per round.

Each round starts with `yield env.timeout(sync_interval_s)`. `rounds`
bounds the number of rounds (None runs forever). Workers are drawn from
the operational pods in the registry; with fewer than two active pods
nothing is emitted.

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
    PATTERN_ALL_REDUCE,
    PATTERN_PARAMETER_SERVER,
    AITrainingSyncProfile,
)
from skynetra.foundation.errors import ConfigError
from skynetra.foundation.types import NodeId


class AITrainingSyncWorkload(WorkloadGenerator):
    """All-reduce / parameter-server gradient sync in rounds."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        fields = AITrainingSyncProfile.__dataclass_fields__
        profile_config = {k: v for k, v in self._config.items() if k in fields}
        self._profile = AITrainingSyncProfile(**profile_config)
        if self._profile.pattern not in (
            PATTERN_ALL_REDUCE,
            PATTERN_PARAMETER_SERVER,
        ):
            raise ConfigError(
                f"Unknown AI training pattern '{self._profile.pattern}'. "
                f"Available: {[PATTERN_ALL_REDUCE, PATTERN_PARAMETER_SERVER]}"
            )
        self._rng = random.Random(self._profile.seed)

    @property
    def profile(self) -> AITrainingSyncProfile:
        return self._profile

    def generate(
        self,
        env: Any,
        publish_packet: Callable[[Packet], None],
        node_registry: dict[NodeId, Node],
    ) -> Iterator[Any]:
        pods = self.get_active_pods(node_registry)
        if len(pods) < 2:
            return
        if self._profile.pattern == PATTERN_PARAMETER_SERVER:
            server = pods[0]
            workers = pods[1:]
        else:
            workers = pods
        profile = self._profile
        round_count = 0
        while profile.rounds is None or round_count < profile.rounds:
            yield env.timeout(profile.sync_interval_s)
            if profile.pattern == PATTERN_PARAMETER_SERVER:
                for worker in workers:
                    publish_packet(
                        self.create_packet(
                            env,
                            worker,
                            server,
                            profile.gradient_size_bytes,
                            profile.packet_type,
                            priority=profile.priority,
                        )
                    )
            else:
                for src in workers:
                    for dst in workers:
                        if src != dst:
                            publish_packet(
                                self.create_packet(
                                    env,
                                    src,
                                    dst,
                                    profile.gradient_size_bytes,
                                    profile.packet_type,
                                    priority=profile.priority,
                                )
                            )
            round_count += 1
