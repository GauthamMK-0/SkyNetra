# Extension Guide

This guide covers how external code (third-party plugins) and internal code outside the `skynetra` package composes with SkyNetra via the stable L0-L2 public interfaces.

## Contract

Third parties may depend **only** on layers L0, L1, and L2:

| Layer | What Is Available |
|-------|-------------------|
| L0 | Types (`NodeId`, `Vector3`, `TimeSeconds`), errors, `EventBus`, math utils |
| L1 | `Node`, `PhysicsState`, `MetricsState`, `Packet`, `PropagatorInterface` |
| L2 | ABCs (`RoutingEngine`, `PhysicsModel`, `WorkloadGenerator`), registry `STRATEGIES` dicts |

L3 (`skynetra.orchestration`) and L4 (`skynetra.interface`) are **not** part of the external API. Third-party code must not import from them.

## Extension Mechanisms

There are two ways to supply custom strategies:

### Option A: Register into the Global Registry

Subclass the appropriate ABC, implement the methods, and register in the
module-level `STRATEGIES` dict. This is the simplest approach.

```python
# my_package/my_router.py
from skynetra.foundation.types import NodeId
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES

class MyRouter(RoutingEngine):
    def compute_route(self, graph, source, dest):
        return []

    def name(self) -> str:
        return "my_router"

STRATEGIES["my_router"] = MyRouter
```

Because `STRATEGIES` is a plain dict, any code that imports the module triggers
registration. The simulator can then look up your strategy by name:

```python
from skynetra.engines.routing.registry import get_router
router = get_router("my_router")
```

### Option B: Pass Instances Directly to `from_layers()`

If you prefer not to mutate the global registry, instantiate your strategy
and pass it directly:

```python
from skynetra import SkyNetraSimulation

my_router = MyRouter(...)
sim = SkyNetraSimulation.from_layers(
    nodes=nodes,
    routing_engine=my_router,
    ...
)
```

This works with any object satisfying the ABC interface. The global
`STRATEGIES` dict is never touched.

## What Extension Code Must Provide

| ABC | Required Methods |
|-----|------------------|
| `RoutingEngine` | `compute_route(graph, source, destination) -> List[NodeId]` and `name() -> str` |
| `PhysicsModel` | `apply(states, dt) -> Dict[NodeId, PhysicsState]` and `name() -> str` |
| `WorkloadGenerator` | `generate(current_time, nodes) -> List[Packet]` and `name() -> str` |

## What Extension Code Must Not Do

- Import from `skynetra.orchestration` or `skynetra.interface`
- Import from private modules (anything not in `__all__`)
- Depend on internal implementation details of built-in strategies
- Modify internal simulation state outside the ABC contract

## Extension Examples

See `extensions_examples/` in the repository:

| File | What It Shows |
|------|---------------|
| `energy_aware_router.py` | Custom routing engine using power weights |
| `debris_proximity_model.py` | Custom physics model for debris radiation |
| `fl_metrics_collector.py` | Custom metrics collector (orchestration-level, internal use) |
