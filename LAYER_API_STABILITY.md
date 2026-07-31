# Layer API Stability

## L0 — Foundation  (STABLE v0.1)
- `skynetra.foundation.types`
- `skynetra.foundation.errors`
- `skynetra.foundation.eventbus`
- `skynetra.foundation.math_utils`
- `skynetra.foundation.time_utils`

## L1 — Domain  (STABLE v0.1)
- `skynetra.domain.orbit.constellation`
- `skynetra.domain.orbit.propagator` (interface only)
- `skynetra.domain.topology.isl`
- `skynetra.domain.topology.graph`
- `skynetra.domain.nodes.base`
- `skynetra.domain.packets.packet`

## L2 — Engines  (STABLE v0.1)
- `skynetra.engines.routing.interface`
- `skynetra.engines.physics.interface`
- `skynetra.engines.workload.interface`
- Concrete strategy implementations: STABLE

## L3 — Orchestration  (STABLE / EXPERIMENTAL)
- `skynetra.orchestration.context` — STABLE v0.1
- `skynetra.orchestration.events` — STABLE v0.1
- `skynetra.orchestration.results` — STABLE v0.1
- `skynetra.orchestration.engine` — EXPERIMENTAL (internal loop may change)
- `skynetra.orchestration.metrics` — STABLE v0.1

## L4 — Interface  (STABLE / EXPERIMENTAL)
- `skynetra.interface.config` — STABLE v0.1
- `skynetra.interface.cli` — STABLE v0.1
- `skynetra.interface.reporting` — STABLE v0.1
- `skynetra.interface.viz` — EXPERIMENTAL (API may change in minor releases)
