"""
Domain layer (L1) — ground station node.

A ground station is the terrestrial edge of the network: it receives
packets downlinked from space (`process_packet`) and transmits packets
uplinked to space (`send_uplink`). Uplink/downlink counters live in the
metrics state; GSL scheduling and elevation gating are Layer 2/3
concerns.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId


class GroundStationNode(Node):
    """Terrestrial edge node with uplink/downlink counters."""

    def __init__(
        self,
        node_id: NodeId,
        latitude: float = 0.0,
        longitude: float = 0.0,
        altitude_m: float = 0.0,
        event_bus: EventBus | None = None,
    ) -> None:
        super().__init__(node_id, node_type="ground", event_bus=event_bus)
        self._latitude = latitude
        self._longitude = longitude
        self._altitude_m = altitude_m
        self._metrics_state["uplink_packets"] = 0
        self._metrics_state["downlink_packets"] = 0

    @property
    def latitude(self) -> float:
        return self._latitude

    @property
    def longitude(self) -> float:
        return self._longitude

    @property
    def altitude_m(self) -> float:
        return self._altitude_m

    def process_packet(self, packet: Packet) -> bool:
        """Receive a downlinked packet from a satellite.

        Returns False (and increments the dropped counter) when the
        station is faulted.
        """
        if not self._begin_packet_processing(packet):
            return False
        self._metrics_state["downlink_packets"] += 1
        self._metrics_state["packets_received"] += 1
        self._publish("packet_downlinked", {"packet_id": packet.packet_id})
        return True

    def send_uplink(self, packet: Packet) -> bool:
        """Transmit a packet uplinked to a satellite.

        Returns False (and increments the dropped counter) when the
        station is faulted.
        """
        if not self._begin_packet_processing(packet):
            return False
        self._metrics_state["uplink_packets"] += 1
        self._metrics_state["packets_sent"] += 1
        self._publish("packet_uplinked", {"packet_id": packet.packet_id})
        return True

    def get_queue_depth(self) -> int:
        # A ground station does not buffer; packets are handled immediately.
        return 0

    def get_utilization(self) -> float:
        return 0.0
