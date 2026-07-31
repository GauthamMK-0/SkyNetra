# Examples

Each example script lives in `examples/` and can be run directly:

```bash
python examples/basic_relay_run.py
```

## `basic_relay_run.py`

**What it demonstrates:** Minimal SkyNetra setup with three relay satellites and one ground station. Uses `ShortestPathRouter` and two metrics collectors (`Network`, `Topology`). No physics or workload generators.

Key steps:
1. Create `RelayNode` and `GroundStation` instances
2. Pass them as a dict to `SkyNetraSimulation`
3. Run for 5 seconds
4. Print all metrics

## `sdc_shortest_path.py`

**What it demonstrates:** A full SDC scenario with relays, compute pods, and a ground station. Combines physics models (`ThermalModel`, `RadiationModel`) via `PhysicsOrchestrator`, generates AI-training workload, and collects four metric types.

Key steps:
1. Create mixed node types (`RelayNode`, `PodNode`, `GroundStation`)
2. Set initial `PhysicsState` on all nodes
3. Build `PhysicsOrchestrator` with two physics models
4. Create `AITrainingWorkload` from a `WorkloadProfile`
5. Run for 100 seconds
6. Inspect per-category metrics

## `sdc_backpressure.py`

**What it demonstrates:** Same SDC setup as `sdc_shortest_path.py` but uses `BackPressureRouter` instead. Shows how to seed queue backlogs via `update_backlog()` to influence routing decisions.

Key steps:
1. Identical node setup and physics configuration
2. Use `BackPressureRouter` with manual backlog values
3. Run for 100 seconds
4. Compare metrics against the shortest-path variant

## `scaling_sweep.py`

**What it demonstrates:** Parametric scaling study across constellation sizes `[2, 4, 8, 16, 32]`. Builds N relay satellites plus one ground station, runs a short simulation, and tabulates edges, degree, packets, and drops.

Key steps:
1. Loop over constellation sizes
2. Build nodes with `build_constellation(n)`
3. Run each simulation for 10 seconds
4. Print formatted table of results

## `custom_physics_model.py`

**What it demonstrates:** How to write and use a custom `PhysicsModel` without modifying the `skynetra` source. Defines `SolarFlareModel` that adds radiation dose at a configurable rate.

Key steps:
1. Subclass `PhysicsModel` and implement `apply()` and `name()`
2. Register in `STRATEGIES` (optional — can pass instance directly)
3. Build `PhysicsOrchestrator` containing only the custom model
4. Run simulation and inspect per-node radiation dose

## `custom_routing_strategy.py`

**What it demonstrates:** How to write and use a custom `RoutingEngine`. Defines `SimpleHopRouter` that uses unweighted shortest path.

Key steps:
1. Subclass `RoutingEngine` and implement `compute_route()` and `name()`
2. Register in `STRATEGIES` (or pass directly)
3. Use with `SkyNetraSimulation` alongside `NetworkMetricsCollector`

## `custom_metrics_collector.py`

**What it demonstrates:** How to write a custom `MetricsCollector` at the orchestration layer. Defines `LatencyMetricsCollector` that estimates total hops from `packets_sent`.

Key steps:
1. Subclass `MetricsCollector` and implement `collect()` and `name()`
2. Register in the metrics `STRATEGIES` dict
3. Pass to `SkyNetraSimulation` alongside or instead of built-in collectors

## Extension Examples (`extensions_examples/`)

These files live outside the main `skynetra` package to demonstrate the third-party extension pattern:

| File | Description |
|------|-------------|
| `energy_aware_router.py` | Routing engine that prefers nodes with higher available power |
| `debris_proximity_model.py` | Physics model that adds debris-related radiation dose |
| `fl_metrics_collector.py` | Metrics collector that tracks federated-learning rounds |
