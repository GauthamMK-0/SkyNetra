# SkyNetra

SkyNetra is a simulation toolkit for evaluating compute-aware routing in space-based data center (SDC) networks.

## Architecture

The codebase is structured in five strictly ordered layers:

| Layer | Package | Responsibility |
|-------|---------|----------------|
| L0 | `skynetra.foundation` | Pure utilities, type aliases, error hierarchy, event bus |
| L1 | `skynetra.domain` | Orbit/topology/node/packet data models and ABCs |
| L2 | `skynetra.engines` | Routing, physics, workload algorithms |
| L3 | `skynetra.orchestration` | SimPy simulation core, events, metrics |
| L4 | `skynetra.interface` | Config, CLI, visualization, reporting |

**Rule:** A layer may import only from itself or from layers strictly below it. This is enforced mechanically via `import-linter` and an AST-based CI check.

## Quick Start

```python
from skynetra import SkyNetraSimulation, FullConfig
from skynetra.domain.nodes.relay import RelayNode
from skynetra.engines.routing.shortest_path import ShortestPathRouter

nodes = {NodeId("sat-1"): RelayNode(NodeId("sat-1"))}
sim = SkyNetraSimulation(nodes=nodes, routing_engine=ShortestPathRouter())
results = sim.run(duration=100.0)
print(results.metrics)
```

## Installation

```bash
pip install -e .
```

## Testing

```bash
pytest
```

## Layer Boundary Enforcement

```bash
import-linter .
```
