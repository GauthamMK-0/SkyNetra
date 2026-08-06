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

## Simulation Semantics

The L3 core (`SkyNetraSimulation` / `OrbitDCSimulation`) models a compute-capable LEO constellation. The following semantics are the contract the engines expose:

- **Propagation** — satellites move on circular Kepler orbits (`ReferenceCircularPropagator`, L1) in an inertial (ECI) frame.
- **Earth rotation** — ground stations and pods are Earth-fixed: their inertial positions rotate at the sidereal rate (`EARTH_SIDEREAL_RATE_RAD_S`). Topology is rebuilt periodically (`topology_update_interval_s`); each rebuild rotates station positions to `time_s`, so GSL edges appear and disappear as satellite elevation crosses the mask.
- **GSL elevation mask** — a GSL edge exists only when the satellite's elevation at the ground station is at least `gsl_elevation_min_deg` (default 10°), configurable end-to-end via `FullConfig.ground_stations.gsl_elevation_min_deg`.
- **Link capacities** — ISL edges default to 100 Gbps, GSL edges to 10 Gbps (`NetworkConfig`); a shared (GSL) link splits its capacity across the satellites currently visible at the station.
- **Queueing / transmission delay** — every link is a `simpy.PriorityResource`. Transmitting `packet.size_bytes` over a link takes `size*8 / (capacity * effective_capacity_fraction * 1e9)` seconds; packets queue at the link, served by `packet.priority`, then travel for the propagation delay of the edge. Relay queues are FIFO and bounded (`RELAY_QUEUE_CAPACITY`); each link's queue drains to zero when idle — there is no phantom backlog.
- **Compute service time** — pods execute queued tasks (`ComputeJobCompleteEvent.compute_latency_s`) with `service = flops_required / available_compute_flops()`, where available FLOPS degrade with temperature and radiation dose. This replaced the former fixed aggregate delay (no fake `aggregate_time_s`).
- **Routing contracts** — shortest-path routing never transits a pod (pods are endpoints only); backpressure reads live queue pressure and compute backlog per decision, refuses U-turns, and breaks weight ties toward the destination so it cannot lock into closed rings. Both routers respect a per-packet hop cap (`MAX_FORWARD_HOPS`).
