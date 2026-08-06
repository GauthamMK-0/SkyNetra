"""
Domain layer (L1) — compute pod node.

A pod hosts on-orbit compute: it accepts packets into a bounded compute
queue; the Layer 3 compute loop dispatches queued tasks via
`take_next_task` and records completion via `record_compute`, accruing
FLOPS and energy metrics. The degradation of available compute from
thermal load and radiation dose is a deterministic Layer 1 formula;
Layer 2 physics engines push the temperature/dose values in via
`update_physics`, and scheduler/workload algorithms (Layer 2/3) decide
what gets queued.

May import from: itself, domain, foundation.
"""

from __future__ import annotations

from collections import deque

from skynetra.domain.nodes.base import Node
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId

POD_QUEUE_CAPACITY = 100


class PodNode(Node):
    """Compute pod with a bounded task queue and FLOPS degradation."""

    def __init__(
        self,
        node_id: NodeId,
        flops: float = 1e12,
        memory_gb: float = 16.0,
        storage_gb: float = 100.0,
        event_bus: EventBus | None = None,
    ) -> None:
        super().__init__(node_id, node_type="pod", event_bus=event_bus)
        self._flops = flops
        self._memory_gb = memory_gb
        self._storage_gb = storage_gb
        self._queue: deque[Packet] = deque()

    @property
    def flops(self) -> float:
        return self._flops

    @property
    def memory_gb(self) -> float:
        return self._memory_gb

    @property
    def storage_gb(self) -> float:
        return self._storage_gb

    def available_compute_flops(self) -> float:
        """Effective compute throughput after thermal and radiation
        degradation of the nominal FLOPS budget.
        """
        return (
            self._flops
            * self.thermal_degradation_factor()
            * self.radiation_degradation_factor()
        )

    def process_packet(self, packet: Packet) -> bool:
        """Accept a compute task into the queue.

        Returns False (and increments the dropped counter) when the node
        is faulted or the queue is full.
        """
        if not self._begin_packet_processing(packet):
            return False
        if self.get_queue_depth() >= POD_QUEUE_CAPACITY:
            self._metrics_state["packets_dropped"] += 1
            self._publish("packet_dropped", {"packet_id": packet.packet_id})
            return False
        self._queue.append(packet)
        self._metrics_state["packets_received"] += 1
        self._publish("packet_accepted", {"packet_id": packet.packet_id})
        return True

    def take_next_task(self) -> Packet | None:
        """Pop the oldest queued compute task for service.

        Called by the Layer 3 compute loop when it dispatches a task to
        the pod's service; the task is removed from the queue so pending
        backlog (read by load-aware routing) reflects tasks still
        awaiting service. Returns None when the queue is empty.
        """
        if not self._queue:
            return None
        return self._queue.popleft()

    def record_compute(self, packet: Packet) -> None:
        """Accrue completion metrics for a serviced task: task and FLOPS
        counters plus an energy estimate based on the currently
        available compute rate. Service time is a Layer 3 concern.
        """
        self._metrics_state["compute_tasks"] += 1
        self._metrics_state["compute_flops"] += packet.flops_required
        self._metrics_state["energy_consumed"] += (
            packet.flops_required / max(1.0, self.available_compute_flops())
        )
        self._metrics_state["packets_sent"] += 1
        self._publish("packet_computed", {"packet_id": packet.packet_id})

    def get_queue_depth(self) -> int:
        return len(self._queue)

    def get_utilization(self) -> float:
        """Fraction of the compute queue currently in use."""
        return self.get_queue_depth() / POD_QUEUE_CAPACITY
