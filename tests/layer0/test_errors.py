from __future__ import annotations

from skynetra.foundation.errors import (
    ConfigError,
    LayerViolationError,
    MetricsError,
    PhysicsError,
    RoutingError,
    SimulationError,
    SkyNetraError,
    WorkloadError,
)


def test_skynetra_error_is_base():
    assert issubclass(ConfigError, SkyNetraError)
    assert issubclass(LayerViolationError, SkyNetraError)
    assert issubclass(SimulationError, SkyNetraError)
    assert issubclass(PhysicsError, SkyNetraError)
    assert issubclass(RoutingError, SkyNetraError)
    assert issubclass(WorkloadError, SkyNetraError)
    assert issubclass(MetricsError, SkyNetraError)


def test_instanceof_checks():
    exc = ConfigError("bad config")
    assert isinstance(exc, SkyNetraError)
    assert isinstance(exc, ConfigError)
    assert not isinstance(exc, SimulationError)


def test_error_message():
    msg = "test message"
    exc = SkyNetraError(msg)
    assert str(exc) == msg


def test_layer_violation():
    exc = LayerViolationError("layer violation detected")
    assert isinstance(exc, SkyNetraError)


def test_simulation_error():
    exc = SimulationError("sim failed")
    assert isinstance(exc, SimulationError)


def test_physics_error():
    exc = PhysicsError("orbit invalid")
    assert isinstance(exc, PhysicsError)
    assert isinstance(exc, SkyNetraError)


def test_routing_error():
    exc = RoutingError("no path found")
    assert isinstance(exc, RoutingError)
    assert isinstance(exc, SkyNetraError)


def test_workload_error():
    exc = WorkloadError("generation failed")
    assert isinstance(exc, WorkloadError)
    assert isinstance(exc, SkyNetraError)


def test_metrics_error():
    exc = MetricsError("collection failed")
    assert isinstance(exc, MetricsError)
    assert isinstance(exc, SkyNetraError)


def test_all_subclasses_distinct():
    subclasses = {
        ConfigError,
        LayerViolationError,
        SimulationError,
        PhysicsError,
        RoutingError,
        WorkloadError,
        MetricsError,
    }
    assert len(subclasses) == 7
