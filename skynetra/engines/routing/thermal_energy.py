"""
Engines layer (L2) — thermal and energy-aware routing engine (TEHR).

Space-environment aware routing designed for LEO satellite constellations:
Penalizes routing through overheated satellites (T > 320 K) and satellites
operating under depleted battery power during orbital eclipse umbras.
Ensures constellations maintain thermal stability and energy reserves while
delivering packets with bounded delay.

May import from: itself, engines, domain, foundation.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.engines.routing.interface import RoutingEngine
from skynetra.foundation.types import LinkId, NodeId


class ThermalEnergyAwareRouter(RoutingEngine):
    """Thermal and Energy-Harvesting Aware Router (TEHR).

    Dynamically routes around satellites approaching thermal throttling
    thresholds or experiencing battery depletion during eclipses.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._alpha_delay = float(self._config.get("alpha_delay", 1.0))
        self._beta_thermal = float(self._config.get("beta_thermal", 15.0))
        self._gamma_energy = float(self._config.get("gamma_energy", 25.0))
        self._delta_queue = float(self._config.get("delta_queue", 10.0))
        self._temp_nominal_k = float(self._config.get("temp_nominal_k", 300.0))
        self._temp_throttle_k = float(self._config.get("temp_throttle_k", 340.0))
        self._power_nominal_w = float(self._config.get("power_nominal_w", 1000.0))
        self._power_critical_w = float(self._config.get("power_critical_w", 200.0))

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

        # Direct edge fast path if operational
        if graph.has_edge(current_node_id, packet.dst):
            dst_node = node_registry.get(packet.dst)
            if dst_node is None or dst_node.is_operational():
                return packet.dst

        operational_graph = self.filter_operational_nodes(graph, node_registry)
        if current_node_id not in operational_graph or packet.dst not in operational_graph:
            return None

        # Compute dynamic edge weights considering propagation, thermal load, and energy
        def weight_fn(u: NodeId, v: NodeId, attrs: dict[str, Any]) -> float:
            base_delay = float(attrs.get("propagation_delay_ms", 1.0))
            if weight_overrides:
                base_delay += float(weight_overrides.get(LinkId(f"{u}->{v}"), 0.0))

            cost = self._alpha_delay * base_delay

            # Read target node's physical state from registry
            target_node = node_registry.get(v)
            if target_node is not None:
                # 1. Thermal penalty: exponential growth above nominal
                p_state = target_node.physics_state
                temp_k = float(p_state.get("temperature_k", self._temp_nominal_k))
                if temp_k > self._temp_nominal_k:
                    excess_temp = temp_k - self._temp_nominal_k
                    temp_range = max(1.0, self._temp_throttle_k - self._temp_nominal_k)
                    thermal_ratio = excess_temp / temp_range
                    cost += self._beta_thermal * (thermal_ratio ** 2)

                # 2. Energy penalty: penalize low battery reserves
                power_w = float(p_state.get("power_available_w", self._power_nominal_w))
                if power_w < self._power_nominal_w:
                    power_ratio = max(0.01, power_w / self._power_nominal_w)
                    cost += self._gamma_energy * ((1.0 / power_ratio) - 1.0)

                # 3. Queue occupancy penalty
                cost += self._delta_queue * target_node.get_utilization()

            return cost

        try:
            path = nx.shortest_path(
                operational_graph,
                source=current_node_id,
                target=packet.dst,
                weight=weight_fn,
            )
            if len(path) >= 2:
                return NodeId(path[1])
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        return None
