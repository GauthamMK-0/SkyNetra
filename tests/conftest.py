from __future__ import annotations

from typing import Dict

import pytest

from skynetra.domain.orbit.constellation import ConstellationConfig
from skynetra.domain.packets.packet import Packet
from skynetra.foundation.eventbus import EventBus
from skynetra.foundation.types import NodeId, Vector3


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def sample_vector3() -> Vector3:
    return (1.0, 2.0, 3.0)


@pytest.fixture
def constellation_3x3() -> ConstellationConfig:
    return ConstellationConfig(
        n_planes=3,
        sats_per_plane=3,
        altitude_km=550.0,
        inclination_deg=53.0,
        phase_offset_f=1,
        raan_spread_deg=360.0,
    )


@pytest.fixture
def sample_packet() -> Packet:
    return Packet(
        packet_id="pkt-001",
        src=NodeId("relay-a"),
        dst=NodeId("gs-1"),
        size_bytes=1500,
        packet_type="data",
        created_at=0.0,
    )


@pytest.fixture
def node_positions() -> Dict[NodeId, Vector3]:
    return {
        NodeId("sat-1"): (7000.0, 0.0, 0.0),
        NodeId("sat-2"): (0.0, 7000.0, 0.0),
        NodeId("sat-3"): (0.0, 0.0, 7000.0),
    }
