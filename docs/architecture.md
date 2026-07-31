# Architecture

SkyNetra is organised into five strictly ordered layers. A layer may import only from itself or from layers below it. This rule is enforced mechanically via `import-linter` and an AST-based CI check.

## Layer Table

| Layer | Package | Responsibility | Imports From |
|-------|---------|----------------|--------------|
| L4 | `skynetra.interface` | Config (Pydantic), CLI (Click), viz (matplotlib/plotly), reporting | L3, L2, L1, L0 |
| L3 | `skynetra.orchestration` | SimPy simulation core, events, context, metrics aggregation, results | L2, L1, L0 |
| L2 | `skynetra.engines` | Routing, physics, workload algorithms and registries | L1, L0 |
| L1 | `skynetra.domain` | Orbit, topology, nodes, packets data models and ABCs | L0 |
| L0 | `skynetra.foundation` | Type aliases, error hierarchy, event bus, math utils, logging | itself only |

## What Each Layer Provides

| Layer | Public API |
|-------|------------|
| L0 | `NodeId`, `LinkId`, `Vector3`, `TimeSeconds`, exception classes, `EventBus`, `configure_logging`, Kepler/geometry math, sim-time conversion |
| L1 | `ConstellationConfig`, `PropagatorInterface`, `build_topology_graph`, ISL visibility/link quality, `Node`/`RelayNode`/`PodNode`/`GroundStation`, `PhysicsState`, `MetricsState`, `Packet` |
| L2 | `RoutingEngine` ABC, `ShortestPathRouter`, `BackPressureRouter`, `PhysicsModel` ABC, `ThermalModel`, `RadiationModel`, `PowerModel`, `DopplerModel`, `PhysicsOrchestrator`, `WorkloadGenerator` ABC, `AITrainingWorkload`, `InferenceWorkload`, `FederatedLearningWorkload`, `WorkloadProfile`, strategy registries |
| L3 | `SkyNetraSimulation` (and `from_layers()`), `SimulationContext`, `SimulationResults`, typed event classes, `MetricsCollector` ABC, `MetricsAggregator`, built-in metric collectors |
| L4 | `FullConfig`, `load_config`, `save_config`, `skynetra_cli`, `export_results`, `compare_runs`, viz functions |

## Strict Dependency Rule

Each layer's `__init__.py` contains a docstring declaring what it may import from:

```
# skynetra/foundation/__init__.py  →  May import from: itself only.
# skynetra/domain/__init__.py      →  May import from: itself, foundation (L0).
# skynetra/engines/__init__.py     →  May import from: itself, domain (L1), foundation (L0).
# skynetra/orchestration/__init__.py →  May import from: itself, engines (L2), domain (L1), foundation (L0).
# skynetra/interface/__init__.py   →  May import from: any layer below (L0-L3).
```

Enforcement is done by:
1. **import-linter** — configured in `.importlinter` with a `layers` contract
2. **AST-based pytest** — `tests/layer_boundaries/test_no_upward_imports.py` scans every `.py` file and asserts no upward imports

## Public API Convention

Names exported from each package's `__init__.py` (in `__all__`) constitute the public API. Anything not listed in `__all__` is private and should not be imported from outside the owning layer. Internal subpackage imports (e.g. `from skynetra.engines.routing.shortest_path import ShortestPathRouter`) are permitted within the same layer but discouraged across layers.

## Layer Ordering

```
┌──────────────────────────────┐
│  L4  skynetra.interface      │
├──────────────────────────────┤
│  L3  skynetra.orchestration  │
├──────────────────────────────┤
│  L2  skynetra.engines        │
├──────────────────────────────┤
│  L1  skynetra.domain         │
├──────────────────────────────┤
│  L0  skynetra.foundation     │
└──────────────────────────────┘
```

Code in a higher layer may always use types from any lower layer. Code in a lower layer must never import from a higher layer.
