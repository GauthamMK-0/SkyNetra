from __future__ import annotations

import math

import pytest

from skynetra.domain.nodes.base import (
    DEFAULT_METRICS_STATE,
    DEFAULT_PHYSICS_STATE,
    Node,
    NodeEvent,
)
from skynetra.domain.nodes.ground import GroundStationNode
from skynetra.domain.nodes.pod import PodNode
from skynetra.domain.nodes.relay import RELAY_QUEUE_CAPACITY, RelayNode
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId


def _packet(packet_id: str = "pkt-1", flops_required: float = 1e9) -> Packet:
    return Packet(
        packet_id=packet_id,
        src=NodeId("relay-a"),
        dst=NodeId("relay-b"),
        size_bytes=1500,
        packet_type="data",
        created_at=0.0,
        flops_required=flops_required,
    )


class TestNodeBase:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Node(NodeId("n-1"), "relay")  # type: ignore[abstract]

    def test_default_state_schemas(self):
        node = RelayNode(NodeId("r-1"))
        assert node.physics_state == DEFAULT_PHYSICS_STATE
        assert node.metrics_state == DEFAULT_METRICS_STATE

    def test_update_physics_merges(self):
        node = RelayNode(NodeId("r-1"))
        node.update_physics({"temperature_k": 320.0, "radiation_dose_rad": 50.0})
        assert node.physics_state["temperature_k"] == 320.0
        assert node.physics_state["radiation_dose_rad"] == 50.0
        assert node.physics_state["power_available_w"] == 1000.0

    def test_update_physics_partial_delta(self):
        node = RelayNode(NodeId("r-1"))
        node.update_physics({"fault_probability": 0.2})
        assert node.physics_state["fault_probability"] == 0.2
        assert node.physics_state["temperature_k"] == 293.15

    def test_thermal_degradation_formula(self):
        node = RelayNode(NodeId("r-1"))
        assert node.thermal_degradation_factor() == 1.0
        node.update_physics({"temperature_k": 350.0})
        assert node.thermal_degradation_factor() == pytest.approx(math.exp(-1.0))

    def test_radiation_degradation_formula(self):
        node = RelayNode(NodeId("r-1"))
        assert node.radiation_degradation_factor() == 1.0
        node.update_physics({"radiation_dose_rad": 1000.0})
        assert node.radiation_degradation_factor() == pytest.approx(0.5)

    def test_snapshot_shape(self):
        node = RelayNode(NodeId("r-1"))
        snapshot = node.snapshot()
        assert snapshot["node_id"] == NodeId("r-1")
        assert snapshot["node_type"] == "relay"
        assert snapshot["operational"] is True
        assert snapshot["physics_state"] == DEFAULT_PHYSICS_STATE
        assert snapshot["metrics_state"] == DEFAULT_METRICS_STATE

    def test_snapshot_is_a_copy(self):
        node = RelayNode(NodeId("r-1"))
        snapshot = node.snapshot()
        node.update_physics({"temperature_k": 350.0})
        assert snapshot["physics_state"]["temperature_k"] == 293.15
        assert node.physics_state["temperature_k"] == 350.0


class TestFaultBehavior:
    def test_fault_probability_disables_node(self):
        node = RelayNode(NodeId("r-1"))
        node.update_physics({"fault_probability": 0.9})
        assert not node.is_operational()

    def test_temperature_threshold_disables_node(self):
        node = RelayNode(NodeId("r-1"))
        node.update_physics({"temperature_k": 450.0})
        assert not node.is_operational()

    def test_faulted_node_drops_packets(self):
        node = RelayNode(NodeId("r-1"))
        node.update_physics({"fault_probability": 0.9})
        assert node.process_packet(_packet()) is False
        assert node.metrics_state["packets_dropped"] == 1
        assert node.metrics_state["packets_received"] == 0
        assert node.get_queue_depth() == 0

    def test_recovering_node_accepts_packets(self):
        node = RelayNode(NodeId("r-1"))
        node.update_physics({"fault_probability": 0.9})
        assert node.process_packet(_packet()) is False
        node.update_physics({"fault_probability": 0.0})
        assert node.is_operational()
        assert node.process_packet(_packet()) is True

    def test_fault_drop_applies_to_all_node_types(self):
        pod = PodNode(NodeId("pod-1"))
        pod.update_physics({"fault_probability": 0.9})
        assert pod.process_packet(_packet()) is False
        ground = GroundStationNode(NodeId("gs-1"))
        ground.update_physics({"fault_probability": 0.9})
        assert ground.process_packet(_packet()) is False


class TestRelayNode:
    def test_accepts_into_forwarding_queue(self):
        node = RelayNode(NodeId("r-1"))
        assert node.process_packet(_packet("pkt-1")) is True
        assert node.get_queue_depth() == 1
        assert node.metrics_state["packets_received"] == 1

    def test_forward_packet_empties_queue(self):
        node = RelayNode(NodeId("r-1"))
        packet = _packet("pkt-1")
        node.process_packet(packet)
        assert node.forward_packet() is packet
        assert node.get_queue_depth() == 0
        assert node.metrics_state["packets_sent"] == 1

    def test_forward_packet_empty_queue(self):
        node = RelayNode(NodeId("r-1"))
        assert node.forward_packet() is None

    def test_utilization(self):
        node = RelayNode(NodeId("r-1"))
        assert node.get_utilization() == 0.0
        for i in range(10):
            node.process_packet(_packet(f"pkt-{i}"))
        assert node.get_utilization() == pytest.approx(0.1)

    def test_full_queue_drops(self):
        node = RelayNode(NodeId("r-1"))
        for i in range(RELAY_QUEUE_CAPACITY):
            assert node.process_packet(_packet(f"pkt-{i}")) is True
        assert node.process_packet(_packet("overflow")) is False
        assert node.metrics_state["packets_dropped"] == 1


class TestPodNode:
    def test_creation_defaults(self):
        pod = PodNode(NodeId("pod-1"))
        assert pod.flops == 1e12
        assert pod.memory_gb == 16.0
        assert pod.storage_gb == 100.0

    def test_creation_custom(self):
        pod = PodNode(NodeId("pod-2"), flops=2e12, memory_gb=32.0, storage_gb=500.0)
        assert pod.flops == 2e12
        assert pod.memory_gb == 32.0
        assert pod.storage_gb == 500.0

    def test_available_compute_flops_degradation(self):
        pod = PodNode(NodeId("pod-1"), flops=1e12)
        assert pod.available_compute_flops() == pytest.approx(1e12)
        pod.update_physics({"temperature_k": 350.0, "radiation_dose_rad": 1000.0})
        assert pod.available_compute_flops() == pytest.approx(
            1e12 * math.exp(-1.0) * 0.5
        )

    def test_take_next_task_dispatches_oldest(self):
        pod = PodNode(NodeId("pod-1"))
        first = _packet("pkt-1", flops_required=2e9)
        second = _packet("pkt-2", flops_required=3e9)
        assert pod.process_packet(first) is True
        assert pod.process_packet(second) is True
        assert pod.get_queue_depth() == 2
        assert pod.take_next_task() is first
        assert pod.take_next_task() is second
        assert pod.get_queue_depth() == 0

    def test_record_compute_accrues_metrics(self):
        pod = PodNode(NodeId("pod-1"))
        packet = _packet("pkt-1", flops_required=2e9)
        assert pod.process_packet(packet) is True
        assert pod.take_next_task() is packet
        pod.record_compute(packet)
        assert pod.metrics_state["compute_tasks"] == 1
        assert pod.metrics_state["compute_flops"] == 2e9
        assert pod.metrics_state["energy_consumed"] > 0.0

    def test_take_next_task_empty_queue(self):
        pod = PodNode(NodeId("pod-1"))
        assert pod.take_next_task() is None


class TestGroundStationNode:
    def test_creation_defaults(self):
        gs = GroundStationNode(NodeId("gs-1"))
        assert gs.latitude == 0.0
        assert gs.longitude == 0.0
        assert gs.altitude_m == 0.0

    def test_creation_custom(self):
        gs = GroundStationNode(NodeId("gs-2"), latitude=37.0, longitude=-122.0, altitude_m=100.0)
        assert gs.latitude == 37.0
        assert gs.longitude == -122.0
        assert gs.altitude_m == 100.0

    def test_downlink_counter(self):
        gs = GroundStationNode(NodeId("gs-1"))
        packet = _packet("pkt-1")
        assert gs.process_packet(packet) is True
        assert gs.metrics_state["downlink_packets"] == 1
        assert gs.metrics_state["packets_received"] == 1

    def test_uplink_counter(self):
        gs = GroundStationNode(NodeId("gs-1"))
        packet = _packet("pkt-1")
        assert gs.send_uplink(packet) is True
        assert gs.metrics_state["uplink_packets"] == 1
        assert gs.metrics_state["packets_sent"] == 1

    def test_no_queue(self):
        gs = GroundStationNode(NodeId("gs-1"))
        assert gs.get_queue_depth() == 0
        assert gs.get_utilization() == 0.0


class TestEventBusInjection:
    def test_injected_bus_receives_events(self):
        bus = EventBus()
        events: list[NodeEvent] = []
        bus.subscribe(NodeEvent, events.append)
        node = RelayNode(NodeId("r-1"), event_bus=bus)
        node.process_packet(_packet("pkt-1"))
        node.forward_packet()
        node.update_physics({"fault_probability": 0.9})
        node.process_packet(_packet("pkt-2"))
        assert [event.event_type for event in events] == [
            "packet_accepted",
            "packet_forwarded",
            "packet_dropped",
        ]
        assert all(event.node_id == NodeId("r-1") for event in events)

    def test_default_bus_is_per_node(self):
        node_a = RelayNode(NodeId("r-1"))
        node_b = RelayNode(NodeId("r-2"))
        assert node_a.event_bus is not node_b.event_bus
        assert isinstance(node_a.event_bus, EventBus)

    def test_injected_bus_is_used_not_global(self):
        bus = EventBus()
        node = RelayNode(NodeId("r-1"), event_bus=bus)
        assert node.event_bus is bus
