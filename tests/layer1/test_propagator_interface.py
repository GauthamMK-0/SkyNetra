from __future__ import annotations

from typing import Dict

import pytest

from skynetra.domain.orbit.propagator import PropagatorInterface
from skynetra.foundation.types import NodeId, Vector3


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        PropagatorInterface()  # type: ignore[abstract]


class MinimalPropagator(PropagatorInterface):
    def __init__(self) -> None:
        self._epoch = 0.0

    def propagate(
        self, positions: Dict[NodeId, Vector3], dt: float
    ) -> Dict[NodeId, Vector3]:
        return {nid: (x, y + dt, z) for nid, (x, y, z) in positions.items()}

    def get_epoch(self) -> float:
        return self._epoch

    def set_epoch(self, epoch: float) -> None:
        self._epoch = epoch

    def reset(self, epoch: float) -> None:
        self._epoch = epoch


@pytest.fixture
def propagator() -> MinimalPropagator:
    return MinimalPropagator()


class TestMinimalPropagator:
    def test_is_propagator_interface(self, propagator: MinimalPropagator):
        assert isinstance(propagator, PropagatorInterface)

    def test_propagate_returns_positions(self, propagator: MinimalPropagator):
        positions = {NodeId("sat-1"): (7000.0, 0.0, 0.0)}
        result = propagator.propagate(positions, 1.0)
        assert NodeId("sat-1") in result
        assert result[NodeId("sat-1")] == (7000.0, 1.0, 0.0)

    def test_get_epoch_default(self, propagator: MinimalPropagator):
        assert propagator.get_epoch() == 0.0

    def test_set_epoch(self, propagator: MinimalPropagator):
        propagator.set_epoch(100.0)
        assert propagator.get_epoch() == 100.0

    def test_reset(self, propagator: MinimalPropagator):
        propagator.set_epoch(200.0)
        propagator.reset(0.0)
        assert propagator.get_epoch() == 0.0

    def test_propagate_multiple_nodes(self, propagator: MinimalPropagator):
        positions = {
            NodeId("a"): (1.0, 2.0, 3.0),
            NodeId("b"): (4.0, 5.0, 6.0),
        }
        result = propagator.propagate(positions, 0.5)
        assert len(result) == 2
        assert result[NodeId("a")] == (1.0, 2.5, 3.0)
        assert result[NodeId("b")] == (4.0, 5.5, 6.0)
