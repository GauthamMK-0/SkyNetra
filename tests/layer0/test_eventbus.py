from __future__ import annotations

import logging
from dataclasses import dataclass

import pytest

from skynetra.foundation.eventbus import EventBus


@dataclass
class SampleEvent:
    value: int = 0


@dataclass
class OtherEvent:
    msg: str = ""


@dataclass
class BaseEvent:
    kind: str = "base"


@dataclass
class DerivedEvent(BaseEvent):
    detail: int = 0


class StubEnv:
    def __init__(self) -> None:
        self.t = 0.0
        self.processes = []

    def timeout(self, delay: float) -> object:
        self.t += delay
        return ("timeout", self.t)

    def process(self, gen) -> object:
        self.processes.append(gen)
        return gen


def test_subscribe_and_publish():
    bus = EventBus()
    received: list[SampleEvent] = []

    def handler(ev: SampleEvent) -> None:
        received.append(ev)

    bus.subscribe(SampleEvent, handler)
    bus.publish(SampleEvent(42))
    assert len(received) == 1
    assert received[0].value == 42


def test_multiple_handlers():
    bus = EventBus()
    results: list[int] = []

    def h1(ev: SampleEvent) -> None:
        results.append(ev.value * 2)

    def h2(ev: SampleEvent) -> None:
        results.append(ev.value * 3)

    bus.subscribe(SampleEvent, h1)
    bus.subscribe(SampleEvent, h2)
    bus.publish(SampleEvent(10))
    assert results == [20, 30]


def test_unsubscribe():
    bus = EventBus()
    received: list[SampleEvent] = []

    def handler(ev: SampleEvent) -> None:
        received.append(ev)

    bus.subscribe(SampleEvent, handler)
    bus.publish(SampleEvent(1))
    bus.unsubscribe(SampleEvent, handler)
    bus.publish(SampleEvent(2))
    assert len(received) == 1


def test_clear():
    bus = EventBus()
    received: list[SampleEvent] = []

    def handler(ev: SampleEvent) -> None:
        received.append(ev)

    bus.subscribe(SampleEvent, handler)
    bus.clear()
    bus.publish(SampleEvent(99))
    assert len(received) == 0


def test_different_event_types():
    bus = EventBus()
    sample_events: list[SampleEvent] = []
    other_events: list[OtherEvent] = []

    def sample_handler(ev: SampleEvent) -> None:
        sample_events.append(ev)

    def other_handler(ev: OtherEvent) -> None:
        other_events.append(ev)

    bus.subscribe(SampleEvent, sample_handler)
    bus.subscribe(OtherEvent, other_handler)
    bus.publish(SampleEvent(1))
    bus.publish(OtherEvent("hi"))
    assert len(sample_events) == 1
    assert len(other_events) == 1
    assert other_events[0].msg == "hi"


def test_no_subscribers_no_error():
    bus = EventBus()
    bus.publish(SampleEvent(5))


def test_unsubscribe_nonexistent():
    bus = EventBus()

    def handler(ev: SampleEvent) -> None:
        pass

    bus.unsubscribe(SampleEvent, handler)


def test_priority_ordering():
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe(SampleEvent, lambda ev: calls.append("low"), priority=10)
    bus.subscribe(SampleEvent, lambda ev: calls.append("high"), priority=1)
    bus.publish(SampleEvent())
    assert calls == ["high", "low"]


def test_equal_priority_insertion_order():
    bus = EventBus()
    calls: list[int] = []

    def h1(ev: SampleEvent) -> None:
        calls.append(1)

    def h2(ev: SampleEvent) -> None:
        calls.append(2)

    bus.subscribe(SampleEvent, h1)
    bus.subscribe(SampleEvent, h2)
    bus.publish(SampleEvent())
    assert calls == [1, 2]


def test_exception_isolation(caplog):
    bus = EventBus()
    good: list[int] = []

    def bad(ev: SampleEvent) -> None:
        raise RuntimeError("boom")

    def ok(ev: SampleEvent) -> None:
        good.append(ev.value)

    bus.subscribe(SampleEvent, bad)
    bus.subscribe(SampleEvent, ok)
    with caplog.at_level(logging.ERROR):
        bus.publish(SampleEvent(7))
    assert good == [7]


def test_exception_does_not_abort_bus():
    bus = EventBus()
    calls: list[int] = []

    def bad(ev: SampleEvent) -> None:
        raise ValueError("nope")

    def ok(ev: SampleEvent) -> None:
        calls.append(1)

    bus.subscribe(SampleEvent, bad, priority=1)
    bus.subscribe(SampleEvent, ok, priority=2)
    bus.publish(SampleEvent())
    assert calls == [1]


def test_inheritance_dispatch():
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe(BaseEvent, lambda ev: calls.append("base"))
    bus.subscribe(DerivedEvent, lambda ev: calls.append("derived"))
    bus.publish(DerivedEvent(detail="x"))
    assert calls == ["base", "derived"]


def test_inheritance_publish_bare_base_does_not_alert_derived():
    bus = EventBus()
    derived_calls: list[str] = []
    bus.subscribe(DerivedEvent, lambda ev: derived_calls.append("d"))
    bus.publish(BaseEvent())
    assert derived_calls == []


def test_get_subscriber_count():
    bus = EventBus()
    bus.subscribe(SampleEvent, lambda ev: None)
    bus.subscribe(SampleEvent, lambda ev: None)
    bus.subscribe(OtherEvent, lambda ev: None)
    assert bus.get_subscriber_count(SampleEvent) == 2
    assert bus.get_subscriber_count(OtherEvent) == 1
    assert bus.get_subscriber_count(BaseEvent) == 0


def test_publish_async_with_stub_env():
    bus = EventBus()
    received: list[SampleEvent] = []
    bus.subscribe(SampleEvent, lambda ev: received.append(ev))

    env = StubEnv()
    proc = bus.publish_async(env, SampleEvent(7), delay_s=5.0)
    assert len(env.processes) == 1
    assert env.t == 0.0
    assert received == []

    marker = next(proc)
    assert env.t == 5.0
    assert received == []
    with pytest.raises(StopIteration):
        proc.send(marker)
    assert received == [SampleEvent(7)]


def test_publish_async_zero_delay():
    bus = EventBus()
    received: list[SampleEvent] = []
    bus.subscribe(SampleEvent, lambda ev: received.append(ev))

    env = StubEnv()
    proc = bus.publish_async(env, SampleEvent(1), delay_s=0.0)
    with pytest.raises(StopIteration):
        next(proc)
    assert received == [SampleEvent(1)]


def test_subscribed_handlers_executed_exactly_once():
    bus = EventBus()
    n = [0]

    def inc(ev: SampleEvent) -> None:
        n[0] += 1

    bus.subscribe(SampleEvent, inc)
    bus.publish(SampleEvent())
    bus.publish(SampleEvent())
    assert n[0] == 2
