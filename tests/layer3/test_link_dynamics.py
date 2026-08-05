"""
L3 tests — link/queue dynamics (Phase 1).

Covers the engine transmit step rewrite: per-link `simpy.PriorityResource`
with transmission delay, relay queue dequeue at transmit time, and the
ISL/GSL capacity split.

Topology used throughout (deterministic):
    1 plane x 2 sats, 550 km; gs-1 at (R,0,0) with sat-0-0 directly
    overhead (elevation 90 deg) and sat-0-1 on the far side (no GSL).
    pod-1 attaches to both sats. So the path gs-1 -> sat-0-0 -> pod-1 is
    forced, and both hops are GSL-class links.
"""

from __future__ import annotations

from typing import Any

import pytest

from skynetra.domain.nodes.base import Node
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RelayNode
from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.orbit.propagator import ReferenceCircularPropagator
from skynetra.engines.routing.registry import get_routing_engine
from skynetra.engines.workload.interface import WorkloadGenerator
from skynetra.foundation.types import NodeId
from skynetra.interface.config.defaults import FullConfig, config_to_simulation_spec
from skynetra.orchestration.engine import OrbitDCSimulation
from skynetra.orchestration.events import PacketDeliveredEvent

CONSTELLATION_1X2 = ConstellationConfig(
    n_planes=1, sats_per_plane=2, altitude_km=550, inclination_deg=55
)

# 100 MB at 10 Gbps = 80 ms transmission per GSL hop.
BIG_SIZE_BYTES = 100_000_000
BIG_TX_S = 0.080

GS_1 = NodeId("gs-1")
POD_1 = NodeId("pod-1")


class TwoPacketWorkload(WorkloadGenerator):
    """Emits two identical packets src->dst, optionally back-to-back,
    with configurable priorities. Records the emitted packet ids."""

    def __init__(
        self,
        src: NodeId,
        dst: NodeId,
        size_bytes: int,
        interval_s: float = 0.0,
        priorities: tuple[int, int] = (0, 0),
    ) -> None:
        super().__init__()
        self._src = src
        self._dst = dst
        self._size_bytes = size_bytes
        self._interval_s = interval_s
        self._priorities = priorities
        self.packet_ids: list[str] = []

    def generate(
        self,
        env: Any,
        publish_packet: Any,
        node_registry: dict[NodeId, Node],
    ) -> Any:
        for priority in self._priorities:
            packet = self.create_packet(
                env, self._src, self._dst, self._size_bytes, "test", priority=priority
            )
            self.packet_ids.append(packet.packet_id)
            publish_packet(packet)
            yield env.timeout(self._interval_s)


def _registry() -> dict[NodeId, Node]:
    propagator = ReferenceCircularPropagator()
    registry: dict[NodeId, Node] = {
        sat_id: RelayNode(sat_id) for sat_id in propagator.get_sat_ids(CONSTELLATION_1X2)
    }
    registry[POD_1] = PodNode(POD_1)
    registry[GS_1] = GroundStationNode(GS_1)
    return registry


def _sim(workloads: list[WorkloadGenerator], **kwargs: object) -> OrbitDCSimulation:
    return OrbitDCSimulation.from_layers(
        constellation=CONSTELLATION_1X2,
        node_registry=_registry(),
        routing_engine=get_routing_engine("shortest_path"),
        workloads=workloads,
        topology_update_interval_s=1000.0,
        **kwargs,
    )


def _deliveries(results: Any) -> dict[str, float]:
    """Map packet_id -> end-to-end latency for delivered packets."""
    return {
        event.packet.packet_id: event.latency_s
        for event in results.events
        if isinstance(event, PacketDeliveredEvent)
    }


class TestLinkSerialization:
    def test_back_to_back_packets_serialize_on_shared_link(self):
        workload = TwoPacketWorkload(GS_1, POD_1, BIG_SIZE_BYTES, interval_s=0.0)
        results = _sim([workload], sim_duration_s=10.0).run()

        latencies = _deliveries(results)
        assert len(latencies) == 2
        first, second = sorted(latencies.values())

        # The second packet waits for the first on both shared links; its
        # hop-1 transmission overlaps the first packet's hop-2 transmission,
        # so the delay penalty is exactly one hop's transmission time.
        assert second - first == pytest.approx(BIG_TX_S, abs=1e-3)

    def test_spaced_packets_do_not_contend(self):
        workload = TwoPacketWorkload(GS_1, POD_1, BIG_SIZE_BYTES, interval_s=5.0)
        results = _sim([workload], sim_duration_s=10.0).run()

        latencies = _deliveries(results)
        first, second = sorted(latencies.values())
        assert second - first == pytest.approx(0.0, abs=1e-6)

    def test_priority_packet_served_first(self):
        # A leading jammer holds the shared link from t=0 so both contenders
        # are queued behind it before the link frees; the higher-priority
        # (lower number) packet must then be served first.
        jammer = TwoPacketWorkload(GS_1, POD_1, BIG_SIZE_BYTES, interval_s=0.0, priorities=(0,))
        contenders = TwoPacketWorkload(
            GS_1, POD_1, BIG_SIZE_BYTES, interval_s=0.0, priorities=(5, 1)
        )
        results = _sim([jammer, contenders], sim_duration_s=10.0).run()

        delivered = sorted(
            (event for event in results.events if isinstance(event, PacketDeliveredEvent)),
            key=lambda ev: ev.time,
        )
        order = [event.packet.packet_id for event in delivered]
        assert order == [
            jammer.packet_ids[0],
            contenders.packet_ids[1],  # priority 1 (higher) before priority 5
            contenders.packet_ids[0],
        ]


class TestQueueDrain:
    def test_relay_queues_drain_after_transmission(self):
        workload = TwoPacketWorkload(GS_1, POD_1, BIG_SIZE_BYTES, interval_s=5.0)
        sim = _sim([workload], sim_duration_s=10.0)
        sim.run()

        for node_id, node in sim.setup().node_registry.items():
            if isinstance(node, RelayNode):
                assert node.get_queue_depth() == 0
                assert node.get_utilization() == 0.0

    def test_relay_packets_sent_matches_transits(self):
        workload = TwoPacketWorkload(GS_1, POD_1, BIG_SIZE_BYTES, interval_s=5.0)
        sim = _sim([workload], sim_duration_s=10.0)
        results = sim.run()

        relay = sim.setup().node_registry[NodeId("sat-0-0")]
        assert relay.metrics_state["packets_sent"] == 2
        assert results.engine_metrics["network_metrics"]["dropped"] == 0


class TestCapacityWiring:
    def test_config_translation_preserves_capacities(self):
        config = FullConfig(
            network={"isl_capacity_gbps": 200.0, "gsl_capacity_gbps": 30.0}
        )
        spec = config_to_simulation_spec(config)
        assert spec.isl_capacity_gbps == 200.0
        assert spec.gsl_capacity_gbps == 30.0

    def test_graph_edges_carry_split_capacities(self):
        config = FullConfig(
            network={"isl_capacity_gbps": 200.0, "gsl_capacity_gbps": 30.0}
        )
        sim = OrbitDCSimulation.from_spec(config_to_simulation_spec(config))
        graph = sim.setup().graph

        isl_edge = graph.edges[NodeId("sat-0-0"), NodeId("sat-0-1")]
        assert isl_edge["capacity"] == 200.0

        gsl_edge = graph.edges[GS_1, NodeId("sat-0-0")]
        assert gsl_edge["capacity"] == 30.0

        pod_edge = graph.edges[POD_1, NodeId("sat-0-0")]
        assert pod_edge["capacity"] == 30.0
