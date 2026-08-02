"""
Domain layer (L1) — relay satellite node.

A relay is a store-and-forward node: it accepts packets into a bounded
forwarding queue and hands them onward via `forward_packet`. It carries
no routing algorithm — deciding the next hop is a Layer 2 routing
concern that reads the queue state.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from collections import deque

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId

RELAY_QUEUE_CAPACITY = 100


class RelayNode(Node):
    """Store-and-forward relay satellite with a bounded forwarding queue."""

    def __init__(self, node_id: NodeId, event_bus: EventBus | None = None) -> None:
        super().__init__(node_id, node_type="relay", event_bus=event_bus)
        self._queue: deque[Packet] = deque()

    def process_packet(self, packet: Packet) -> bool:
        """Accept a packet into the forwarding queue.

        Returns False (and increments the dropped counter) when the node
        is faulted or the queue is full.
        """
        if not self._begin_packet_processing(packet):
            return False
        if self.get_queue_depth() >= RELAY_QUEUE_CAPACITY:
            self._metrics_state["packets_dropped"] += 1
            self._publish("packet_dropped", {"packet_id": packet.packet_id})
            return False
        self._queue.append(packet)
        self._metrics_state["packets_received"] += 1
        self._publish("packet_accepted", {"packet_id": packet.packet_id})
        return True

    def forward_packet(self) -> Packet | None:
        """Dequeue the oldest buffered packet for transmission.

        Returns the packet and increments the sent counter, or None when
        the queue is empty.
        """
        if not self._queue:
            return None
        packet = self._queue.popleft()
        self._metrics_state["packets_sent"] += 1
        self._publish("packet_forwarded", {"packet_id": packet.packet_id})
        return packet

    def get_queue_depth(self) -> int:
        return len(self._queue)

    def get_utilization(self) -> float:
        """Fraction of the forwarding queue currently in use."""
        return self.get_queue_depth() / RELAY_QUEUE_CAPACITY
