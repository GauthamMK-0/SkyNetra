# SkyNetra

**SkyNetra** is a high-performance simulation toolkit for evaluating compute-aware routing in Space-Based Data Center (SDC) networks.

SkyNetra models Low Earth Orbit (LEO) satellite constellations equipped with on-orbit compute accelerators (pods), inter-satellite laser links (ISLs), Earth-fixed ground stations, and dynamic space environment physics (thermal eclipse cycles, solar/battery power, radiation dose, and Doppler shifts).

---

## Key Features

- **5-Layer Architecture**: Strict downward-only dependency enforcement (L4 $\to$ L3 $\to$ L2 $\to$ L1 $\to$ L0) mechanically verified by `import-linter` and AST checks.
- **High-Level 3-Line API**: Execute end-to-end simulations, print terminal telemetry dashboards, and export publication-ready plots in 3 lines.
- **Constellation & Topology Dynamics**: Walker-Delta constellations on circular Keplerian orbits, Earth sidereal rotation, line-of-sight ISLs, and elevation-gated GSLs.
- **On-Orbit Compute Pods**: Dynamic task queueing and execution with hardware degradation from radiative thermal stress and cumulative radiation dose.
- **Adaptive Routing Strategies**:
  - `ShortestPathRouter`: Dijkstra baseline minimizing latency, hop count, or inverse capacity.
  - `BackPressureRouter`: Load-aware routing considering queue pressure, compute backlog, link delay, and physics penalties with anti-looping guarantees.
- **Space Physics Engine**: Radiative thermal heating/cooling across eclipse cycles, solar array & battery state-of-charge, radiation SEU/latchups, and line-of-sight Doppler shifts.
- **Distributed Workload Models**:
  - `ai_training_sync`: Distributed gradient all-reduce synchronization.
  - `inference_query`: Realistic Poisson/bursty query traffic toward compute pods.
  - `federated_learning`: 3-phase on-orbit worker upload, aggregator pod fusion, and broadcast.
- **Rich Telemetry & Reporting**: Formatted terminal dashboards (`results.report()`), typed metrics accessors (`results.network`, `results.compute`, `results.physics`, `results.topology`), and automated chart exports (`results.plot()`).

---

## 5-Layer Architectural Contract

| Layer | Package | Core Responsibility | Permitted Imports |
| :--- | :--- | :--- | :--- |
| **L4** | `skynetra.interface` | High-level API (`simulate`), Pydantic configs (`FullConfig`), Click CLI, plotting, reporting | L3, L2, L1, L0 |
| **L3** | `skynetra.orchestration` | SimPy discrete-event core, PriorityResource scheduling, metrics collectors, results | L2, L1, L0 |
| **L2** | `skynetra.engines` | Routing engines, space physics models, workload generators, strategy registries | L1, L0 |
| **L1** | `skynetra.domain` | Constellation topology, ISL/GSL graphs, node hardware models (Relay, Pod, Ground), packets | L0 |
| **L0** | `skynetra.foundation` | Type aliases (`NodeId`, `LinkId`), error hierarchy, priority `EventBus`, math & time utilities | Itself only |

---

## Quick Start

### Mode 1: 3-Line High-Level API (Recommended)

```python
import skynetra as sn

# 1. Run simulation with intuitive parameters
results = sn.simulate(
    duration_s=60.0,
    constellation="3x6",    # 3 planes x 6 satellites = 18 sats
    pods=2,                 # 2 on-orbit compute pods
    routing="backpressure", # Adaptive load-aware routing
    workload="inference",   # Inference query traffic
)

# 2. Print formatted multi-section terminal dashboard
results.report()

# 3. Export all 7 visualization plots to disk
results.plot("results/plots")
```

### Mode 2: Advanced Declarative Configuration (`FullConfig`)

```python
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation

config = FullConfig(
    simulation={"duration_s": 120.0, "seed": 42},
    constellation={"n_planes": 6, "sats_per_plane": 10},
    pods={"n_pods": 4},
    ground_stations={"n_ground_stations": 2, "gsl_elevation_min_deg": 10.0},
    routing={"strategy": "backpressure"},
    workload={"active": ["ai_training_sync", "inference_query"]},
    physics={"thermal": {"enabled": True}, "radiation": {"enabled": True}},
)

spec = config_to_simulation_spec(config)
results = OrbitDCSimulation.from_spec(spec).run()

# Access typed metrics directly
print(f"Delivered: {results.network.delivered} packets")
print(f"Mean Latency: {results.network.avg_latency_ms:.2f} ms")
print(f"Compute Tasks Finished: {results.compute.jobs_completed} jobs")
```

---

## Command-Line Interface (CLI)

SkyNetra includes a Click-powered CLI entrypoint:

```bash
# Run simulation with defaults
skynetra run

# Run with custom parameters and strategy
skynetra run --duration 120 --routing backpressure --output results/

# Run parametric parameter sweep across constellations and pods
skynetra sweep --output-dir results/sweep/

# Compare routing strategies side-by-side
skynetra compare --strategies shortest_path,backpressure --duration 60
```

---

## Installation

```bash
# Clone the repository
git clone git@github.com:GauthamMK-0/SkyNetra.git
cd SkyNetra

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

---

## Quality Gates & Verification

SkyNetra maintains a 100% test pass rate, strict static typing, and zero lint warnings:

```bash
# Run unit, layer, and integration tests (510 tests)
pytest

# Verify strict layer boundary enforcement (1 contract kept, 0 broken)
import-linter lint

# Run type checking across all 69 source files
mypy skynetra

# Run fast code linting and formatting checks
ruff check .
```
