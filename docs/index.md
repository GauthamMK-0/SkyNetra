# SkyNetra Documentation

**Simulation toolkit for compute-aware routing in space-based data center (SDC) networks.**

SkyNetra models Low Earth Orbit (LEO) satellite constellations with embedded on-orbit compute pods, store-and-forward relays, Earth-fixed ground stations, and dynamic space physics (thermal eclipse heating/cooling, solar/battery power, radiation dose & latchups, and Doppler shift). The discrete-event simulation core runs on SimPy and coordinates pluggable routing engines, physics models, workload generators, and metrics collectors.

---

## Quick Start

Execute an end-to-end simulation, render a formatted terminal dashboard, and export publication-quality visualization figures in 3 lines:

```python
import skynetra as sn

# 1. Run simulation with sensible defaults
results = sn.simulate(
    duration_s=60.0,
    constellation="3x6",    # 3 planes x 6 satellites = 18 sats
    pods=2,                 # 2 on-orbit compute pods
    routing="backpressure", # Load-adaptive routing
    workload="inference",   # Inference query workload
)

# 2. Render multi-section terminal dashboard
results.report()

# 3. Export all 7 visualization plots
results.plot("results/plots")
```

---

## Installation

```bash
# Basic installation
pip install -e .

# With development and testing dependencies
pip install -e ".[dev]"
```

---

## Key Capabilities

- **5-Layer Architecture**: Strict downward-only dependency hierarchy (L4 $\to$ L3 $\to$ L2 $\to$ L1 $\to$ L0) mechanically verified via `import-linter` and AST scanners.
- **Constellation & Topology Dynamics**: Walker-Delta constellations on Keplerian orbits, Earth sidereal rotation, line-of-sight ISLs, and elevation-gated GSLs.
- **On-Orbit Compute Pods**: Hardware degradation from thermal stress and cumulative radiation dose with real SimPy FLOPS task execution.
- **Pluggable Engines**: Load-aware Backpressure router, Dijkstra shortest path, orbital eclipse thermal models, solar/battery power, and multi-pattern workloads (AI training sync, inference queries, federated learning).
- **Rich Telemetry**: Typed accessors (`results.network`, `results.compute`, `results.physics`, `results.topology`), automated terminal reports, and matplotlib/plotly exports.

---

## Documentation Index

| Page | Description |
| :--- | :--- |
| **[Architecture](architecture.md)** | 5-layer design, downward-only dependency contract, and simulation semantics |
| **[API Reference](api.md)** | Public classes, functions, and interfaces by layer |
| **[Examples](examples.md)** | Walkthrough of all scenario and extension scripts in `examples/` |
| **[Layering Guide](layering_guide.md)** | Adding strategies within each layer without violating boundaries |
| **[Extension Guide](extension_guide.md)** | Composing custom models via L0–L2 public interfaces |
| **[Physics Extensions](physics_extensions.md)** | Implementing custom physics models |
| **[Contributing](contributing.md)** | Development workflow, quality gates, and testing standards |
