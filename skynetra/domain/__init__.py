"""
Domain layer (L1) — orbit/topology/node/packet data models.

May import from: itself, foundation (L0).
"""

from __future__ import annotations

from skynetra.domain.nodes.base import MetricsState, Node, PhysicsState
from skynetra.domain.nodes.ground import GroundStation
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import PropagatorInterface
from skynetra.domain.packets.packet import Packet
from skynetra.domain.topology.graph import build_topology_graph

__all__ = [
    "ConstellationConfig",
    "PropagatorInterface",
    "build_topology_graph",
    "Node",
    "PhysicsState",
    "MetricsState",
    "RelayNode",
    "PodNode",
    "GroundStation",
    "Packet",
]
