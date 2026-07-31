# API Reference

This page lists all public classes and functions exported from the `skynetra` package, grouped by layer and module. The public API is defined by each package's `__all__` list.

## Top-Level (`skynetra`)

| Name | Description |
|------|-------------|
| `SkyNetraSimulation` | Main simulation class; manages the SimPy event loop and coordinates all layers |
| `FullConfig` | Pydantic v2 schema for complete simulation configuration |
| `SimulationResults` | Dataclass holding aggregated metrics, events, and duration |

---

## L0 — Foundation (`skynetra.foundation`)

### Types

| Name | Description |
|------|-------------|
| `NodeId` | NewType over `str` for satellite/ground-station identifiers |
| `LinkId` | NewType over `str` for inter-satellite link identifiers |
| `Vector3` | Tuple `(x, y, z)` for 3-D position/velocity |
| `TimeSeconds` | NewType over `float` for simulation time |

### Errors

| Name | Description |
|------|-------------|
| `SkyNetraError` | Base exception for all SkyNetra errors |
| `ConfigError` | Invalid or incomplete configuration |
| `LayerViolationError` | Illegal cross-layer import detected |
| `SimulationError` | Runtime simulation failure |
| `PhysicsError` | Physics computation failure |
| `RoutingError` | Routing operation failure |
| `WorkloadError` | Workload generation failure |
| `MetricsError` | Metrics collection failure |

### Event Bus

| Name | Description |
|------|-------------|
| `EventBus` | Typed publish/subscribe bus; methods: `subscribe`, `unsubscribe`, `publish`, `clear` |

### Math Utilities

| Name | Description |
|------|-------------|
| `kepler_eccentric_anomaly` | Solve Kepler's equation via Newton-Raphson |
| `rotation_matrix_x` | 3x3 rotation matrix around X axis |
| `rotation_matrix_y` | 3x3 rotation matrix around Y axis |
| `rotation_matrix_z` | 3x3 rotation matrix around Z axis |
| `spherical_to_cartesian` | Convert spherical `(r, theta, phi)` to Cartesian `(x, y, z)` |
| `cartesian_to_spherical` | Convert Cartesian `(x, y, z)` to spherical `(r, theta, phi)` |
| `great_circle_distance` | Haversine distance on a sphere |

### Time Utilities

| Name | Description |
|------|-------------|
| `sim_to_wallclock` | Convert sim seconds to `datetime` (epoch = 2025-01-01 UTC) |
| `wallclock_to_sim` | Convert `datetime` to sim seconds |

### Logging

| Name | Description |
|------|-------------|
| `configure_logging` | Set up stdlib logging (optionally with structlog) |

---

## L1 — Domain (`skynetra.domain`)

### Orbit

| Name | Description |
|------|-------------|
| `ConstellationConfig` | Dataclass for Walker constellation parameters |
| `PropagatorInterface` | ABC for orbital propagation; methods: `propagate`, `get_epoch`, `set_epoch`, `reset` |

### Topology

| Name | Description |
|------|-------------|
| `build_topology_graph` | Build a NetworkX graph from node positions with link-quality thresholding |
| `compute_isl_visibility` | Boolean check whether two positions have line-of-sight above Earth horizon |
| `link_quality` | SNR-based link quality metric from distance |

### Nodes

| Name | Description |
|------|-------------|
| `Node` | Abstract base node with `physics`, `metrics`, `metadata` properties |
| `PhysicsState` | Dataclass: position, velocity, temperature, radiation_dose, power_available, power_consumed |
| `MetricsState` | Dataclass: packets_sent/received/dropped, compute_tasks/flops, energy_consumed |
| `RelayNode` | Simple relay satellite node |
| `PodNode` | Compute pod node with flops, memory, storage |
| `GroundStation` | Ground station with lat/lon/altitude |

### Packets

| Name | Description |
|------|-------------|
| `Packet` | Dataclass: packet_id, source, destination, size_bytes, creation_time, ttl, priority, path, hops, arrived |

---

## L2 — Engines (`skynetra.engines`)

### Routing

| Name | Description |
|------|-------------|
| `RoutingEngine` | ABC with `compute_route(graph, source, destination) -> List[NodeId]` |
| `ShortestPathRouter` | NetworkX shortest-path implementation |
| `BackPressureRouter` | Queue-backlog-aware routing with `update_backlog()` |
| `get_router` | Instantiate routing strategy by name from registry |
| `list_routers` | List registered routing strategy names |
| `STRATEGIES` | Dict mapping strategy names to `Type[RoutingEngine]` |

### Physics

| Name | Description |
|------|-------------|
| `PhysicsModel` | ABC with `apply(states, dt) -> Dict[NodeId, PhysicsState]` |
| `ThermalModel` | Thermal equilibrium model with albedo/emissivity |
| `RadiationModel` | Background radiation dose accumulation |
| `PowerModel` | Solar panel power generation model |
| `DopplerModel` | Doppler shift placeholder |
| `PhysicsOrchestrator` | Chains multiple PhysicsModel instances sequentially |
| `get_physics_model` | Instantiate physics model by name from registry |
| `list_physics_models` | List registered physics model names |
| `STRATEGIES` | Dict mapping model names to `Type[PhysicsModel]` |

### Workload

| Name | Description |
|------|-------------|
| `WorkloadGenerator` | ABC with `generate(current_time, nodes) -> List[Packet]` |
| `WorkloadProfile` | Dataclass: name, packet_size_bytes, generation_rate, priority, ttl, payload_schema |
| `AITrainingWorkload` | All-to-all packet generation among nodes |
| `InferenceWorkload` | Ground-to-space packet generation |
| `FederatedLearningWorkload` | Unidirectional packets to a designated aggregator |
| `get_workload` | Instantiate workload by name from registry |
| `list_workloads` | List registered workload names |
| `STRATEGIES` | Dict mapping workload names to `Type[WorkloadGenerator]` |

---

## L3 — Orchestration (`skynetra.orchestration`)

### Core

| Name | Description |
|------|-------------|
| `SkyNetraSimulation` | Main simulation coordinator; runs the SimPy loop |
| `SimulationContext` | Dataclass holding all mutable simulation state |
| `SimulationResults` | Dataclass: metrics dict, events list, duration |

### Events

| Name | Description |
|------|-------------|
| `SimulationEvent` | Base event dataclass (time, event_type) |
| `SimulationStartEvent` | Published when simulation starts |
| `SimulationEndEvent` | Published when simulation finishes |
| `NodeEvent` | Node-specific event with data dict |
| `PacketEvent` | Packet lifecycle event (generated, forwarded, dropped, arrived) |
| `TopologyEvent` | Topology change event (edge_count, node_count) |
| `PhysicsEvent` | Per-node physics update event |
| `MetricsEvent` | Periodic metrics snapshot event |

### Metrics

| Name | Description |
|------|-------------|
| `MetricsCollector` | ABC with `collect(context) -> Dict[str, Any]` |
| `MetricsAggregator` | Runs all collectors and merges results |
| `NetworkMetricsCollector` | Total packets, dropped, edge/node count |
| `ComputeMetricsCollector` | Total compute tasks and FLOPs |
| `TopologyMetricsCollector` | Average degree, edge/node count |
| `PhysicsMetricsCollector` | Total energy consumed, average temperature |
| `get_metrics_collector` | Instantiate collector by name from registry |
| `list_metrics_collectors` | List registered collector names |

---

## L4 — Interface (`skynetra.interface`)

### Config

| Name | Description |
|------|-------------|
| `FullConfig` | Pydantic model with nested config for all layers |
| `load_config` | Load YAML/JSON config with preset support |
| `save_config` | Serialize FullConfig to YAML or JSON |

### CLI

| Name | Description |
|------|-------------|
| `skynetra_cli` | Click group with `run`, `validate`, `list-strategies` commands |

### Reporting

| Name | Description |
|------|-------------|
| `export_results` | Export metrics dict to JSON or YAML file |
| `compare_runs` | Compare multiple result dicts across specified keys |

### Visualization

| Name | Description |
|------|-------------|
| `plot_network_topology` | Plot NetworkX graph with positions |
| `plot_scaling_results` | Plot scaling-sweep results |
| `plot_isl_connectivity` | Plot ISL connectivity matrix |
| `plot_physics_state` | Plot per-node physics state over time |
