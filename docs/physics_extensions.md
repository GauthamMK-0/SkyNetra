# Physics Extensions

This guide covers writing custom physics models and composing them via the `PhysicsOrchestrator`.

## `PhysicsModel` ABC

All physics models inherit from `skynetra.engines.physics.interface.PhysicsModel`:

```python
class PhysicsModel(ABC):
    @abstractmethod
    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
```

The `apply()` method receives a snapshot of all node physics states and must return a new dict of updated states. The simulation engine calls `apply()` once per timestep.

## The `apply()` Contract

| Aspect | Requirement |
|--------|-------------|
| Input | `Dict[NodeId, PhysicsState]` — one entry per node |
| Output | `Dict[NodeId, PhysicsState]` — must contain **all** input NodeIds |
| Purity | Should not mutate input states; create new `PhysicsState` instances |
| Determinism | Same inputs must produce same outputs (no hidden random state without seed) |
| Performance | Called every timestep; keep per-node computation O(1) |

The physics orchestrator chains multiple models sequentially, so each model should be idempotent and stateless (or maintain its own internal state without relying on previous model output order).

## Writing a Custom Model

### Minimal Example

```python
from typing import Dict

from skynetra.foundation.types import NodeId
from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel


class AtmosphericDragModel(PhysicsModel):
    def __init__(self, drag_coefficient: float = 2.2, density: float = 1e-12) -> None:
        self._cd = drag_coefficient
        self._density = density

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        result = {}
        for nid, state in states.items():
            vx, vy, vz = state.velocity
            speed = (vx**2 + vy**2 + vz**2) ** 0.5
            drag = 0.5 * self._density * speed**2 * self._cd
            # Simple velocity reduction (no direction change for demo)
            factor = 1.0 - drag * dt / max(speed, 1.0)
            result[nid] = PhysicsState(
                position=state.position,
                velocity=(vx * factor, vy * factor, vz * factor),
                temperature=state.temperature + drag * dt * 0.01,
                radiation_dose=state.radiation_dose,
                power_available=state.power_available,
                power_consumed=state.power_consumed,
            )
        return result

    def name(self) -> str:
        return "atmospheric_drag"
```

### Registering the Model

```python
from skynetra.engines.physics.registry import STRATEGIES
STRATEGIES["atmospheric_drag"] = AtmosphericDragModel
```

Or instantiate directly without registration:

```python
drag = AtmosphericDragModel(drag_coefficient=2.5)
```

## Composing Models via `PhysicsOrchestrator`

The `PhysicsOrchestrator` chains multiple models, feeding the output of one as the input to the next:

```python
from skynetra.engines.physics import PhysicsOrchestrator

models = [
    ThermalModel(albedo=0.3),
    RadiationModel(background_dose_rate=0.01),
    PowerModel(solar_panel_area=10.0),
    AtmosphericDragModel(density=1e-13),
]
orchestrator = PhysicsOrchestrator(models)
```

The orchestrator itself is a `PhysicsModel`, so it can be nested or passed directly to `SkyNetraSimulation`:

```python
from skynetra.orchestration.engine import SkyNetraSimulation

sim = SkyNetraSimulation(
    nodes=nodes,
    routing_engine=router,
    physics_orchestrator=orchestrator,
    ...
)
```

### Ordering

Models are applied in the order they appear in the list. This matters when
models share state fields (e.g., a power model that consumes temperature
output from a thermal model). Order models from least-dependent to
most-dependent.

## Built-in Physics Models

| Model | State Fields Modified |
|-------|----------------------|
| `ThermalModel` | `temperature` |
| `RadiationModel` | `radiation_dose` |
| `PowerModel` | `power_available` |
| `DopplerModel` | (none — identity placeholder) |

## Testing Custom Models

Write tests in `tests/layer2/` following the existing pattern:

```python
def test_atmospheric_drag_apply():
    model = AtmosphericDragModel(density=0.0)  # zero density = no drag
    states = {NodeId("s1"): PhysicsState(velocity=(1000.0, 0.0, 0.0))}
    result = model.apply(states, dt=1.0)
    assert result[NodeId("s1")].velocity == (1000.0, 0.0, 0.0)
```

Run with:

```bash
pytest tests/layer2/test_physics_*.py
```
