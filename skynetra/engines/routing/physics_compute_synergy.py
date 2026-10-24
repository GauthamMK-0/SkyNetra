"""
Engines layer (L2) — Physics-Compute Synergy Routing Engine (PCSR).

Custom proposed routing strategy for Space-Based Data Centers (SDCs).
Unifies on-orbit compute pod capacity, queue serialization drain delay,
thermal headroom, radiation tolerance, and orbital link stability into
a joint multi-tier optimization objective:

    Cost(u,v) = w_delay * T_prop(u,v)
              + w_queue * (Q_v / Capacity_uv)
              + w_thermal * (Excess_T_v / Thermal_Headroom)^2
              + w_compute * Pod_Compute_Stress(v)
              + w_rad * (Dose_v / Reference_Dose)
              + weight_overrides(u,v)

Provides proactive load balancing that anticipates compute throttling
and link buffer saturation before packet drops occur.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId


class PhysicsComputeSynergyRouter(RoutingEngine):
    """SkyNetra Physics-Compute Synergy Router (PCSR).
    
    Proactive joint optimization across space environment, orbital dynamics,
    network queue contention, and on-orbit accelerator capacity.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._w_delay = float(self._config.get("w_delay", 1.0))
        self._w_queue = float(self._config.get("w_queue", 40.0))
        self._w_thermal = float(self._config.get("w_thermal", 30.0))
        self._w_compute = float(self._config.get("w_compute", 35.0))
        self._w_radiation = float(self._config.get("w_radiation", 15.0))
        self._w_intra_plane_bias = float(self._config.get("w_intra_plane_bias", 0.5))
        
        self._temp_nominal_k = float(self._config.get("temp_nominal_k", 300.0))
        self._temp_critical_k = float(self._config.get("temp_critical_k", 380.0))
        self._ref_radiation_rad = float(self._config.get("ref_radiation_rad", 1000.0))

    def update_topology(self, new_graph: nx.DiGraph) -> None:
        pass

    def select_next_hop(
        self,
        packet: Packet,
        current_node_id: NodeId,
        graph: nx.DiGraph,
        node_registry: dict[NodeId, Node],
        weight_overrides: dict[LinkId, float] | None = None,
    ) -> NodeId | None:
        if current_node_id == packet.dst:
            return None

        # Direct fast path if neighbor is destination and operational
        if graph.has_edge(current_node_id, packet.dst):
            dst_node = node_registry.get(packet.dst)
            if dst_node is None or dst_node.is_operational():
                return packet.dst

        operational_graph = self.filter_operational_nodes(graph, node_registry)
        if current_node_id not in operational_graph or packet.dst not in operational_graph:
            return None

        # Multi-objective edge cost calculation
        def synergy_weight_fn(u: NodeId, v: NodeId, attrs: dict[str, Any]) -> float:
            prop_delay_ms = float(attrs.get("propagation_delay_ms", 1.0))
            if weight_overrides:
                prop_delay_ms += float(weight_overrides.get(LinkId(f"{u}->{v}"), 0.0))

            capacity_gbps = max(0.1, float(attrs.get("capacity", 10.0)))
            cost = self._w_delay * prop_delay_ms

            # Intra-plane link preference (stability across orbit plane)
            link_type = str(attrs.get("link_type", "isl"))
            if link_type == "isl":
                # Check plane matching: node ids formatted like 'sat_p0_s1'
                u_str, v_str = str(u), str(v)
                if "_p" in u_str and "_p" in v_str:
                    u_plane = u_str.split("_")[1] if len(u_str.split("_")) > 1 else ""
                    v_plane = v_str.split("_")[1] if len(v_str.split("_")) > 1 else ""
                    if u_plane and v_plane and u_plane != v_plane:
                        cost += self._w_intra_plane_bias

            target_node = node_registry.get(v)
            if target_node is not None:
                # 1. Queue drain contention
                cost += self._w_queue * target_node.get_utilization()

                # 2. Thermal stress headroom
                p_state = target_node.physics_state
                temp_k = float(p_state.get("temperature_k", self._temp_nominal_k))
                if temp_k > self._temp_nominal_k:
                    headroom = max(1.0, self._temp_critical_k - self._temp_nominal_k)
                    thermal_ratio = (temp_k - self._temp_nominal_k) / headroom
                    cost += self._w_thermal * (thermal_ratio ** 2)

                # 3. Radiation dose wear-out
                rad_dose = float(p_state.get("radiation_dose_rad", 0.0))
                if rad_dose > 0:
                    cost += self._w_radiation * (rad_dose / self._ref_radiation_rad)

                # 4. On-orbit compute pod backlog & effective FLOPS degradation
                if isinstance(target_node, PodNode):
                    avail_flops = max(1e6, target_node.available_compute_flops())
                    nom_flops = max(1e6, target_node.flops)
                    compute_degradation = nom_flops / avail_flops
                    compute_queue = target_node.get_queue_depth()
                    cost += self._w_compute * (compute_degradation + compute_queue * 0.1)

            return cost

        try:
            path = nx.shortest_path(
                operational_graph,
                source=current_node_id,
                target=packet.dst,
                weight=synergy_weight_fn,
            )
            if len(path) >= 2:
                return NodeId(path[1])
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        return None
