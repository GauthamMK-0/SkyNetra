"""
Foundation layer (L0) — generic typed event bus.

A dependency-free publish/subscribe utility. It knows nothing about
simulation events; skynetra.orchestration defines the typed event
dataclasses and this layer only provides the mechanism.

May import from: itself only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterator, TypeVar, cast

_logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Any)


@dataclass
class _Subscriber:
    priority: int
    seq: int
    callback: Callable[[Any], None]


class EventBus:
    """Publish/subscribe dispatcher with priority ordering.

    Dispatch is inheritance-aware: publishing an event notifies subscribers
    registered on the concrete type as well as every base class in its MRO.
    A failing subscriber never blocks the others; its exception is logged.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[_Subscriber]] = {}
        self._dispatch_cache: dict[type, list[_Subscriber]] = {}
        self._seq_counter = 0

    def subscribe(
        self,
        event_type: type[T],
        callback: Callable[[T], None],
        priority: int = 0,
    ) -> None:
        entry = _Subscriber(
            priority=priority,
            seq=self._seq_counter,
            callback=cast(Callable[[Any], None], callback),
        )
        self._seq_counter += 1
        self._subscribers.setdefault(event_type, []).append(entry)
        self._dispatch_cache.clear()

    def unsubscribe(
        self, event_type: type[Any], callback: Callable[[Any], None]
    ) -> None:
        handlers = self._subscribers.get(event_type)
        if handlers is None:
            return
        for entry in list(handlers):
            if entry.callback is callback:
                handlers.remove(entry)
        if not handlers:
            del self._subscribers[event_type]
        self._dispatch_cache.clear()

    def has_subscribers(self, event_type: type[Any] | None = None) -> bool:
        """True if any subscriber is registered (globally or for `event_type`)."""
        if event_type is None:
            return bool(self._subscribers)
        return bool(self._subscribers.get(event_type))

    def publish(self, event: Any) -> None:
        if not self._subscribers:
            return
        event_type = type(event)
        candidates = self._dispatch_cache.get(event_type)
        if candidates is None:
            candidates_list: list[_Subscriber] = []
            for klass in event_type.__mro__:
                handlers = self._subscribers.get(klass)
                if handlers:
                    candidates_list.extend(handlers)
            candidates_list.sort(key=lambda s: (s.priority, s.seq))
            candidates = candidates_list
            self._dispatch_cache[event_type] = candidates

        for entry in candidates:
            try:
                entry.callback(event)
            except Exception:
                _logger.exception("EventBus subscriber raised on %s", event_type.__name__)

    def publish_async(
        self, env: Any, event: Any, delay_s: float = 0.0
    ) -> Any:
        """Schedule a publish after `delay_s`.

        Returns a process created via `env.process(...)`. `env` is duck-typed
        to expose `.timeout()` and `.process()` (a SimPy Environment); this
        module does not import simpy at module level.
        """
        return env.process(self._delayed_publish(env, event, delay_s))

    def _delayed_publish(
        self, env: Any, event: Any, delay_s: float
    ) -> Iterator[Any]:
        if delay_s > 0:
            yield env.timeout(delay_s)
        self.publish(event)

    def get_subscriber_count(self, event_type: type[Any]) -> int:
        return len(self._subscribers.get(event_type, []))

    def clear(self) -> None:
        self._subscribers.clear()
        self._dispatch_cache.clear()
        self._seq_counter = 0
