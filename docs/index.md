# SkyNetra

**Internal simulation toolkit for compute-aware routing in space-based data center (SDC) networks.**

This documentation is for internal use only. SkyNetra is not open source.

## Overview

SkyNetra models satellite constellations with embedded compute pods, relays, and ground stations, then evaluates routing strategies under realistic physics and workload conditions. The simulation loop runs on SimPy and supports pluggable routing engines, physics models, workload generators, and metrics collectors.

## Quick Start

```python
from skynetra import SkyNetraSimulation
from skynetra.foundation.types import NodeId
from skynetra.domain.nodes import RelayNode
from skynetra.engines.routing import ShortestPathRouter

nodes = {NodeId("sat-1"): RelayNode(NodeId("sat-1"))}
sim = SkyNetraSimulation(nodes=nodes, routing_engine=ShortestPathRouter())
results = sim.run(duration=100.0)
print(results.metrics)
```

## Installation

```bash
pip install -e .
pip install -e ".[dev]"   # with dev dependencies
```

## Key Concepts

- **5-layer architecture** with strict downward-only dependency rules
- **Pluggable engines** for routing, physics, and workload generation
- **Registry pattern** for discovering and selecting strategies
- **Event bus** for decoupled observation of simulation events
- **Metrics collectors** for aggregating simulation output

## Navigation

| Page | Description |
|------|-------------|
| [Architecture](architecture.md) | 5-layer design, dependency rules, public API |
| [Layering Guide](layering_guide.md) | Adding strategies within each layer |
| [Extension Guide](extension_guide.md) | Composing via L0-L2 public interfaces |
| [API Reference](api.md) | Public classes and functions by layer |
| [Examples](examples.md) | Walkthrough of example scripts |
| [Physics Extensions](physics_extensions.md) | Writing custom physics models |
| [Contributing](contributing.md) | Development workflow and standards |
