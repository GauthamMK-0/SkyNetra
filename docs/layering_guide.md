# Layering Guide: Adding a New Strategy

Each of the three engine types (routing, physics, workload) follows the same pattern: subclass an abstract base class (ABC), implement the required methods, and register the new class in the module-level `STRATEGIES` dict.

This guide shows how to add a new strategy within its layer. For external/third-party extensions see the [Extension Guide](extension_guide.md).

## Pattern Overview

1. Create a new module inside the appropriate `skynetra.engines.*` subpackage
2. Subclass the layer's ABC
3. Implement the abstract methods
4. Register in the module-level `STRATEGIES` dict (a side effect at module load)
5. Re-export from the subpackage `__init__.py`

## Example 1: New Routing Engine

File: `skynetra/engines/routing/minimum_latency.py`

```python
from __future__ import annotations

from typing import Dict, List

import networkx as nx

from skynetra.foundation.types import NodeId
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.engines.routing.registry import STRATEGIES


class MinimumLatencyRouter(RoutingEngine):
    def __init__(self, latencies: Dict[str, float] | None = None) -> None:
        self._latencies = latencies or {}

    def compute_route(
        self, graph: nx.Graph, source: NodeId, destination: NodeId
    ) -> List[NodeId]:
        if source not in graph or destination not in graph:
            return []
        try:
            return nx.shortest_path(graph, source=source, target=destination)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def name(self) -> str:
        return "minimum_latency"


STRATEGIES["minimum_latency"] = MinimumLatencyRouter
```

Then export from `skynetra/engines/routing/__init__.py`:

```python
from skynetra.engines.routing.minimum_latency import MinimumLatencyRouter

__all__ = [
    ...
    "MinimumLatencyRouter",
]
```

## Example 2: New Physics Model

File: `skynetra/engines/physics/magnetosphere.py`

```python
from __future__ import annotations

from typing import Dict

from skynetra.foundation.types import NodeId
from skynetra.domain.nodes.base import PhysicsState
from skynetra.engines.physics.interface import PhysicsModel
from skynetra.engines.physics.registry import STRATEGIES


class MagnetosphereModel(PhysicsModel):
    def __init__(self, field_strength: float = 1.0) -> None:
        self._field_strength = field_strength

    def apply(
        self, states: Dict[NodeId, PhysicsState], dt: float
    ) -> Dict[NodeId, PhysicsState]:
        result = {}
        for nid, state in states.items():
            result[nid] = PhysicsState(
                position=state.position,
                velocity=state.velocity,
                temperature=state.temperature,
                radiation_dose=state.radiation_dose + 0.001 * self._field_strength * dt,
                power_available=state.power_available,
                power_consumed=state.power_consumed,
            )
        return result

    def name(self) -> str:
        return "magnetosphere"


STRATEGIES["magnetosphere"] = MagnetosphereModel
```

## Example 3: New Workload Generator

File: `skynetra/engines/workload/video_streaming.py`

```python
from __future__ import annotations

import uuid
from typing import Dict, List

from skynetra.foundation.types import NodeId, TimeSeconds
from skynetra.domain.packets.packet import Packet
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.engines.workload.profiles import WorkloadProfile
from skynetra.engines.workload.registry import STRATEGIES


class VideoStreamingWorkload(WorkloadGenerator):
    def __init__(
        self, profile: WorkloadProfile, ground_nodes: List[NodeId]
    ) -> None:
        self._profile = profile
        self._ground_nodes = ground_nodes

    def generate(
        self, current_time: TimeSeconds, nodes: Dict[NodeId, object]
    ) -> List[Packet]:
        packets = []
        space_nodes = [nid for nid in nodes if nid not in self._ground_nodes]
        for gs in self._ground_nodes:
            for sn in space_nodes:
                packets.append(
                    Packet(
                        packet_id=str(uuid.uuid4()),
                        source=gs,
                        destination=sn,
                        size_bytes=self._profile.packet_size_bytes,
                        creation_time=current_time,
                        ttl=self._profile.ttl,
                        priority=self._profile.priority,
                    )
                )
        return packets

    def name(self) -> str:
        return "video_streaming"


STRATEGIES["video_streaming"] = VideoStreamingWorkload
```

## Registration Mechanics

Each engine subpackage has a `registry.py` that defines a module-level `STRATEGIES: Dict[str, Type[...]]` dict. Concrete implementations register themselves as a side effect:

```python
# At module bottom:
STRATEGIES["my_strategy"] = MyStrategy
```

The registry also exports three helpers:

| Function | Purpose |
|----------|---------|
| `get_*(name, **kwargs)` | Instantiate a strategy by name |
| `list_*()` | List all registered strategy names |
| `STRATEGIES` dict | Direct access for advanced use |

## Composition Rule

Strategies at the same layer may compose freely. For example, `PhysicsOrchestrator` chains multiple `PhysicsModel` instances. A routing engine may call other routing helpers, but may not depend on orchestration or interface types.
