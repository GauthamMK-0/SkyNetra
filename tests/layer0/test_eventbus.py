from __future__ import annotations

from dataclasses import dataclass

from skynetra.foundation.eventbus import EventBus


@dataclass
class SampleEvent:
    value: int = 0


@dataclass
class OtherEvent:
    msg: str = ""


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
