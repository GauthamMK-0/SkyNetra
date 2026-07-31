"""
Foundation layer (L0) — generic typed event bus.

May import from: itself only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Type


@dataclass
class EventBus:
    _subscribers: Dict[Type[Any], List[Callable[[Any], None]]] = field(
        default_factory=dict
    )

    def subscribe(self, event_type: Type[Any], handler: Callable[[Any], None]) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(
        self, event_type: Type[Any], handler: Callable[[Any], None]
    ) -> None:
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Any) -> None:
        for handler in self._subscribers.get(type(event), []):
            handler(event)

    def clear(self) -> None:
        self._subscribers.clear()
