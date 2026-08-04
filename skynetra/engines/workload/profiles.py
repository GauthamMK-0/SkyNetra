"""
Engines layer (L2) — workload profile dataclasses.

Typed configuration shapes for the built-in workload generators. Every
field has a default so generators can be constructed from partial
`config` dicts (`WorkloadGenerator(config=...)`); Layer 3 users build
these dataclasses and pass `dataclasses.asdict(profile)` as the config.

All stochastic behavior is driven by a per-generator `random.Random`
seeded from the profile's `seed` field — no hidden global randomness,
so a fixed seed reproduces the identical packet sequence.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from skynetra.foundation.types import NodeId

PATTERN_ALL_REDUCE = "all_reduce"
PATTERN_PARAMETER_SERVER = "parameter_server"

ARRIVAL_POISSON = "poisson"
ARRIVAL_ON_OFF = "on_off"
ARRIVAL_BURSTY = "bursty"


@dataclass
class AITrainingSyncProfile:
    """Gradient-sync traffic for distributed AI training.

    `pattern` selects the sync scheme:
      all_reduce        — every worker sends its gradient to every other
                           worker: N*(N-1) packets per round.
      parameter_server  — every worker sends to the first active pod
                           (server): N-1 packets per round.
    `rounds=None` runs forever.
    """

    n_workers: int = 8
    gradient_size_bytes: int = 4096
    sync_interval_s: float = 60.0
    pattern: str = PATTERN_ALL_REDUCE
    rounds: int | None = None
    packet_type: str = "ai_training_sync"
    priority: int = 0
    seed: int = 0


@dataclass
class InferenceQueryProfile:
    """Query traffic from ground/edge sources toward compute pods.

    `arrival_pattern` selects the inter-arrival model:
      poisson  — exponentially distributed inter-arrival times with
                 mean `mean_interval_s`.
      on_off   — queries at the poisson rate during `on_duration_s`
                 windows, then silence for `off_duration_s`.
      bursty   — `burst_size` queries spaced `burst_interval_s` apart,
                 then silence for `burst_idle_s`.
    `sources` restricts the querying nodes; empty means any node in the
    registry may query.
    """

    query_size_bytes: int = 256
    mean_interval_s: float = 10.0
    arrival_pattern: str = ARRIVAL_POISSON
    on_duration_s: float = 30.0
    off_duration_s: float = 60.0
    burst_size: int = 5
    burst_interval_s: float = 1.0
    burst_idle_s: float = 120.0
    sources: list[NodeId] = field(default_factory=list)
    packet_type: str = "inference_query"
    priority: int = 0
    seed: int = 0


@dataclass
class FederatedLearningProfile:
    """3-phase federated learning round: gather -> aggregate -> broadcast.

    Each round: every worker sends its model to the aggregator
    (`gather_packet_type`), the aggregator "aggregates" for
    `aggregate_time_s` (no packets — pure compute delay), then the
    aggregator broadcasts the merged model back to every worker
    (`broadcast_packet_type`).
    """

    n_rounds: int = 10
    aggregator: NodeId | None = None
    worker_model_size_bytes: int = 8192
    broadcast_size_bytes: int = 8192
    aggregate_time_s: float = 10.0
    round_interval_s: float = 300.0
    gather_packet_type: str = "fl_gather"
    broadcast_packet_type: str = "fl_broadcast"
    priority: int = 0
    seed: int = 0


@dataclass
class ImageryDownlinkProfile:
    """Satellite-to-ground imagery downlink traffic (profile only).

    No generator is registered for this profile; it documents the
    intended shape for Layer 4/extension workloads.
    """

    image_size_bytes: int = 1048576
    interval_s: float = 600.0
    ground_station: NodeId | None = None
    packet_type: str = "imagery_downlink"
    priority: int = 0
    seed: int = 0
