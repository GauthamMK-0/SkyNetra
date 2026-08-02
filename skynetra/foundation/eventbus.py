"""
Foundation layer (L0) — generic typed event bus.

A dependency-free publish/subscribe utility. It knows nothing about
simulation events; layer3_orchestration defines the typed event
dataclasses and this layer only provides the mechanism.

May import from: itself only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterator, List, TypeVar, cast

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
        self._subscribers: Dict[type, List[_Subscriber]] = {}
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

    def publish(self, event: Any) -> None:
        candidates: List[_Subscriber] = []
        for klass in type(event).__mro__:
            handlers = self._subscribers.get(klass)
            if handlers:
                candidates.extend(handlers)
        candidates.sort(key=lambda s: (s.priority, s.seq))
        for entry in candidates:
            try:
                entry.callback(event)
            except Exception:
                _logger.exception("EventBus subscriber raised on %s", type(event).__name__)

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
        self._seq_counter = 0
