"""
Domain layer (L1) — orbit/topology/node/packet data models.

Layer 1 defines the SHAPES of the simulation: constellation geometry,
the propagator contract (plus one dependency-free reference
implementation), the topology graph schema, node state schemas, and the
packet data model. Swappable ALGORITHMS — propagator strategies, routing,
physics models, workload generators — live in Layer 2
(`skynetra.engines`). Layer 1 never imports anything above itself.

May import from: itself, foundation (L0).
"""

from __future__ import annotations

from skynetra.domain.nodes.base import Node, NodeEvent
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import PropagatorInterface, ReferenceCircularPropagator
from skynetra.domain.packets.packet import Packet
from skynetra.domain.topology.graph import build_topology_graph
from skynetra.domain.topology.isl import (
    compute_gsl_elevation_deg,
    compute_isl_link_quality,
)

__all__ = [
    "ConstellationConfig",
    "PropagatorInterface",
    "ReferenceCircularPropagator",
    "compute_isl_link_quality",
    "compute_gsl_elevation_deg",
    "build_topology_graph",
    "Node",
    "NodeEvent",
    "RelayNode",
    "PodNode",
    "GroundStationNode",
    "Packet",
]
