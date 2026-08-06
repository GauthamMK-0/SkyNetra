"""
Engines layer (L2) — federated learning workload generator.

3-phase federated learning rounds:

  gather     — every worker sends its model to the aggregator
               (`fl_gather` packets, carrying `aggregate_flops`).
  aggregate  — the aggregator pod computes the merged model; service
               time is governed by the pod's compute loop (Layer 3).
  broadcast  — the aggregator sends the merged model back to every
               worker (`fl_broadcast` packets).

Each round starts with `yield env.timeout(round_interval_s)`. The
aggregator defaults to the first operational pod; workers are the
remaining operational pods. With no workers nothing is emitted.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from typing import Any

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import FederatedLearningProfile
from skynetra.foundation.types import NodeId


class FederatedLearningWorkload(WorkloadGenerator):
    """3-phase federated learning rounds: gather -> aggregate -> broadcast."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        fields = FederatedLearningProfile.__dataclass_fields__
        profile_config = {k: v for k, v in self._config.items() if k in fields}
        self._profile = FederatedLearningProfile(**profile_config)
        self._rng = random.Random(self._profile.seed)

    @property
    def profile(self) -> FederatedLearningProfile:
        return self._profile

    def generate(
        self,
        env: Any,
        publish_packet: Callable[[Packet], None],
        node_registry: dict[NodeId, Node],
    ) -> Iterator[Any]:
        pods = self.get_active_pods(node_registry)
        if not pods:
            return
        profile = self._profile
        aggregator = profile.aggregator if profile.aggregator in pods else pods[0]
        workers = [nid for nid in pods if nid != aggregator]
        if not workers:
            return
        for _ in range(profile.n_rounds):
            yield env.timeout(profile.round_interval_s)
            for worker in workers:
                publish_packet(
                    self.create_packet(
                        env,
                        worker,
                        aggregator,
                        profile.worker_model_size_bytes,
                        profile.gather_packet_type,
                        flops_required=profile.aggregate_flops,
                        priority=profile.priority,
                    )
                )
            for worker in workers:
                publish_packet(
                    self.create_packet(
                        env,
                        aggregator,
                        worker,
                        profile.broadcast_size_bytes,
                        profile.broadcast_packet_type,
                        priority=profile.priority,
                    )
                )
