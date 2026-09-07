# Examples

Each example script lives in `examples/` and can be run directly (install the
project first, then):

```bash
python examples/basic_relay_run.py
```

All examples are expressed as a Layer 4 `FullConfig` (translated with
`config_to_simulation_spec` and executed via `OrbitDCSimulation.from_spec`),
except the extension examples, which plug custom Layer 2/3 objects in at the
`from_layers` constructor boundary.

## `basic_run.py`

**What it demonstrates:** The canonical getting-started tutorial showcasing both execution paradigms:
- **Mode 1 (3-Line High-Level API)**: Runs `sn.simulate(duration_s=60.0, constellation="3x6", pods=2, routing="backpressure")`, calls `.report()` for formatted terminal telemetry, and `.plot()` for automated figure generation.
- **Mode 2 (Advanced FullConfig)**: Explicitly constructs a `FullConfig` model with both `ai_training_sync` and `inference_query` workloads, thermal + radiation physics, runs via `OrbitDCSimulation.from_spec(spec).run()`, and demonstrates typed accessors (`results.network`, `results.compute`, `results.physics`, `results.topology`).

## `basic_relay_run.py`

**What it demonstrates:** Ground Station $\to$ Satellite $\to$ Compute Pod relay. Demonstrates GSL access gating, ISL transit, and on-orbit task execution. Prints the two default metric groups (`network_metrics`, `topology_metrics`).

Key steps:
1. Build a `FullConfig` (small constellation, empty workload, reduced metrics)
2. Translate with `config_to_simulation_spec`
3. Run with `OrbitDCSimulation.from_spec(spec).run()`

## `sdc_shortest_path.py`

**What it demonstrates:** A full SDC scenario: 3×6 constellation, 4 compute
pods, 1 ground station, thermal + radiation physics enabled, AI-training sync
(500 MB all-reduce) plus inference workload, all four metric groups, and exports 7 plots.

Key steps:
1. Declare every dimension of the scenario in `FullConfig`
2. Enable physics sections (`thermal`, `radiation`) and their collector
3. Run 120 s, inspect per-category `engine_metrics`, and save plots via `save_all_plots`

## `sdc_backpressure.py`

**What it demonstrates:** The identical scenario with `BackPressureRouter`.
Backpressure is genuinely load-adaptive: it reads live queue pressure and
compute backlog per hop, never transits a pod, and refuses U-turns, so under
light load it matches shortest-path delivery while exploring more hops
(higher `transmitted`, higher latency) as queues build up.

## `sdc_federated_learning.py`

**What it demonstrates:** On-orbit 3-phase Federated Learning:
1. **Worker Upload (Gather)**: Satellites send local model updates across ISLs to a designated aggregator pod.
2. **Aggregator Fusion (Compute)**: Aggregator pod executes parameter averaging and aggregation tasks.
3. **Model Broadcast**: Aggregated global parameters are broadcast back to participating satellites.
Exports all 7 visualization figures showing FL convergence and pod compute latency.

## `scaling_sweep.py`

**What it demonstrates:** Parametric scaling study: every
(constellation size × pod count × routing strategy × physics mode) combination
is run `N_RUNS` times at 1800 s sim time and aggregated as mean ± std. Writes
CSV/JSON results under `results/`, renders the four scaling plots, and prints
an SP-vs-BP comparison table.

Key steps:
1. Loop over sizes `[(3,6), (6,6), (6,10), (10,10)]`, pods `[2,4,8,16]`,
   routers `[shortest_path, backpressure]`, physics `[disabled, thermal_only,
   full_physics]`
2. Build each config as a `FullConfig` with a per-run seed
3. Aggregate and plot

## `custom_physics_model.py`

**What it demonstrates:** How to write and use a custom `PhysicsModel`
without modifying the `skynetra` source. `SolarFlareModel` adds radiation
dose at a configurable rate by implementing `compute_node_physics` /
`compute_link_physics`.

Key steps:
1. Subclass `PhysicsModel` and implement the two abstract methods
2. Register in `STRATEGIES` (optional — the engine resolves specs by name)
3. Add `{"name": "solar_flare", "config": {...}}` to the spec's
   `physics_specs` and run

## `custom_routing_strategy.py`

**What it demonstrates:** How to write and use a custom `RoutingEngine`.
`SimpleHopRouter` uses unweighted BFS via `nx.shortest_path`.

Key steps:
1. Subclass `RoutingEngine` and implement `select_next_hop` and
   `update_topology`
2. Register in `STRATEGIES` (optional)
3. Pass an instance to `OrbitDCSimulation.from_layers` — the L4 `FullConfig`
   `routing.strategy` field is a closed Literal by design, so custom engines
   plug in at the L3 constructor boundary

## `custom_metrics_collector.py`

**What it demonstrates:** How to write a custom `MetricsCollector` at the
orchestration layer. `LatencyMetricsCollector` tallies hops from live
`PacketTransmitEvent`s on the EventBus.

Key steps:
1. Subclass `MetricsCollector` and implement `attach`, `get_summary`,
   `to_dataframe`
2. Register in the metrics `STRATEGIES` dict
3. Add `"latency_metrics"` to `FullConfig.metrics.active`

## Extension Examples (`extensions_examples/`)

These files live outside the main `skynetra` package to demonstrate the third-party extension pattern:

| File | Description |
|------|-------------|
| `energy_aware_router.py` | Routing engine that prefers nodes with higher available power |
| `debris_proximity_model.py` | Physics model that adds debris-related radiation dose |
| `fl_metrics_collector.py` | Metrics collector that tracks federated-learning rounds |
