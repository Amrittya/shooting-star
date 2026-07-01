"""Tests for `ti_core.events`."""

from __future__ import annotations

from typing import Any

import pytest
from ti_core.events import Event, InMemoryEventBus


class OrderPlaced(Event):
    order_id: str
    symbol: str
    quantity: int


class OrderFilled(Event):
    order_id: str
    fill_price: float


@pytest.mark.asyncio
async def test_subscribe_and_publish_single_handler() -> None:
    bus = InMemoryEventBus()
    received: list[OrderPlaced] = []

    async def handler(e: OrderPlaced) -> None:
        received.append(e)

    bus.subscribe(OrderPlaced, handler)
    await bus.publish(OrderPlaced(order_id="o1", symbol="NIFTY", quantity=65))

    assert len(received) == 1
    assert received[0].order_id == "o1"


@pytest.mark.asyncio
async def test_multiple_handlers_all_receive() -> None:
    bus = InMemoryEventBus()
    calls: list[tuple[str, str]] = []

    async def h1(e: OrderPlaced) -> None:
        calls.append(("h1", e.order_id))

    async def h2(e: OrderPlaced) -> None:
        calls.append(("h2", e.order_id))

    bus.subscribe(OrderPlaced, h1)
    bus.subscribe(OrderPlaced, h2)
    await bus.publish(OrderPlaced(order_id="x", symbol="X", quantity=1))

    assert {c[0] for c in calls} == {"h1", "h2"}


@pytest.mark.asyncio
async def test_subscription_is_typed_by_event_class() -> None:
    """Subscribers to OrderPlaced must NOT receive OrderFilled and vice versa."""
    bus = InMemoryEventBus()
    got_placed: list[Any] = []
    got_filled: list[Any] = []

    async def on_placed(e: OrderPlaced) -> None:
        got_placed.append(e)

    async def on_filled(e: OrderFilled) -> None:
        got_filled.append(e)

    bus.subscribe(OrderPlaced, on_placed)
    bus.subscribe(OrderFilled, on_filled)

    await bus.publish(OrderPlaced(order_id="p1", symbol="X", quantity=1))
    await bus.publish(OrderFilled(order_id="p1", fill_price=100.0))

    assert len(got_placed) == 1
    assert len(got_filled) == 1
    assert isinstance(got_placed[0], OrderPlaced)
    assert isinstance(got_filled[0], OrderFilled)


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_is_noop() -> None:
    bus = InMemoryEventBus()
    await bus.publish(OrderPlaced(order_id="ghost", symbol="X", quantity=1))
    # No error, no side-effect.


@pytest.mark.asyncio
async def test_handler_exception_propagates_after_fanout() -> None:
    """One handler raising must not prevent other handlers from running."""
    bus = InMemoryEventBus()
    survivor_ran = False

    async def raising(_: OrderPlaced) -> None:
        raise RuntimeError("boom")

    async def survivor(_: OrderPlaced) -> None:
        nonlocal survivor_ran
        survivor_ran = True

    bus.subscribe(OrderPlaced, raising)
    bus.subscribe(OrderPlaced, survivor)

    with pytest.raises(RuntimeError, match="boom"):
        await bus.publish(OrderPlaced(order_id="e", symbol="X", quantity=1))

    assert survivor_ran, "survivor handler must run even when a peer raises"


@pytest.mark.asyncio
async def test_close_clears_handlers() -> None:
    bus = InMemoryEventBus()
    received: list[OrderPlaced] = []

    async def h(e: OrderPlaced) -> None:
        received.append(e)

    bus.subscribe(OrderPlaced, h)
    await bus.close()
    await bus.publish(OrderPlaced(order_id="post-close", symbol="X", quantity=1))
    assert received == []
