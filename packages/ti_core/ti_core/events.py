"""Event bus abstraction.

Two implementations:

- `InMemoryEventBus`: sync, single-process. Used in tests and backtests.
- `RedisEventBus`: async, cross-process. Uses Redis Streams for durability
  and replay. Used in paper/live modes.

Both implement the same `EventBus` protocol so callers don't care which
backend is in play.

## Design notes

Events are strongly-typed via `pydantic.BaseModel` subclasses. A subscriber
declares the event *class* it wants to receive, not a channel name — the bus
routes by class name. That gives us:

- Compile-time enforcement of the event schema.
- Free JSON serialization for the Redis backend.
- Easy fanout to multiple subscribers with different subsets of events.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from pydantic import BaseModel

TEvent = TypeVar("TEvent", bound=BaseModel)
Handler = Callable[[TEvent], Awaitable[None]]


class Event(BaseModel):
    """Base class for every event that flows on the bus.

    Subclasses must be JSON-serializable via pydantic — no `bytes`, no
    non-`BaseModel` custom types in payloads. Timestamps use `datetime` (UTC).
    """


class EventBus(ABC):
    """Bus protocol. Subscribe to concrete `Event` subclasses; publish concrete instances."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Deliver `event` to all subscribers registered for its concrete type."""

    @abstractmethod
    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Handler[TEvent],
    ) -> None:
        """Register `handler` to receive every event of `event_type`."""

    @abstractmethod
    async def close(self) -> None:
        """Release any resources (Redis connections, etc.)."""


class InMemoryEventBus(EventBus):
    """Single-process bus. Handlers run in the publisher's event loop.

    Not thread-safe. Suitable for tests, backtests, and single-node dev use.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Handler[Event]]] = defaultdict(list)

    async def publish(self, event: Event) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return
        # Run handlers concurrently within this event's fan-out.
        # An exception in one handler must not silently drop delivery to others.
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, BaseException):
                # Re-raise the first exception after all handlers have run.
                # Callers can wrap `publish` in their own error-tolerance if needed.
                raise r

    def subscribe(
        self,
        event_type: type[TEvent],
        handler: Handler[TEvent],
    ) -> None:
        # mypy: variance on Callable is contravariant in the arg; the cast is safe
        # because we only call `handler(event)` where `type(event) is event_type`.
        self._handlers[event_type].append(handler)  # type: ignore[index, arg-type]

    async def close(self) -> None:
        self._handlers.clear()
