"""
Orchestration layer (L3) — simulation context.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId


@dataclass
class SimulationContext:
    nodes: Dict[NodeId, Node] = field(default_factory=dict)
    topology_graph: nx.Graph = field(default_factory=nx.Graph)
    routing_engine: Any = None
    physics_orchestrator: Any = None
    workload_generators: List[WorkloadGenerator] = field(default_factory=list)
    event_bus: EventBus = field(default_factory=EventBus)
    current_time: float = 0.0
    dt: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
