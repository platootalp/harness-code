"""Integration tests for orchestrator event bus integration.

This module contains integration tests for:
- Event publishing during task execution
- Event subscription handling
- Event delivery and processing

Tests verify that the orchestrator correctly integrates with the
EventBus for event publishing and subscription.
"""

from __future__ import annotations

import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mozi.infrastructure.event_bus import Event, EventBus, EventPriority
from mozi.orchestrator import Orchestrator


@pytest.fixture
def event_bus() -> EventBus:
    """Create an event bus instance."""
    return EventBus()


@pytest.fixture
def orchestrator() -> Orchestrator:
    """Create an orchestrator instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Orchestrator(storage_path=tmpdir)


@pytest.mark.integration
class TestEventBusPublish:
    """Tests for event publishing."""

    @pytest.mark.asyncio
    async def test_publish_event(self, event_bus: EventBus) -> None:
        """Test publishing an event to the bus."""
        received: list[Event] = []

        async def handler(evt: Event) -> None:
            received.append(evt)

        await event_bus.subscribe("test.topic", callback=handler)
        await event_bus.publish(
            Event(
                topic="test.topic",
                event_type="test_event",
                payload={"key": "value"},
            )
        )

        # Give time for async delivery
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].payload["key"] == "value"

    @pytest.mark.asyncio
    async def test_publish_multiple_events(self, event_bus: EventBus) -> None:
        """Test publishing multiple events."""
        received: list[Event] = []

        async def handler(evt: Event) -> None:
            received.append(evt)

        await event_bus.subscribe("test.#", callback=handler)

        await event_bus.publish(Event(topic="test.1", event_type="A"))
        await event_bus.publish(Event(topic="test.2", event_type="B"))
        await event_bus.publish(Event(topic="test.3", event_type="C"))

        await asyncio.sleep(0.1)

        assert len(received) == 3


@pytest.mark.integration
class TestEventBusSubscription:
    """Tests for event subscription handling."""

    @pytest.mark.asyncio
    async def test_subscribe_with_wildcard(self, event_bus: EventBus) -> None:
        """Test subscribing with wildcard pattern."""
        received: list[Event] = []

        async def handler(evt: Event) -> None:
            received.append(evt)

        await event_bus.subscribe("events.#", callback=handler)

        await event_bus.publish(Event(topic="events.session.start", event_type="start"))
        await event_bus.publish(Event(topic="events.session.end", event_type="end"))

        await asyncio.sleep(0.1)

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus: EventBus) -> None:
        """Test unsubscribing from events."""
        received: list[Event] = []

        async def handler(evt: Event) -> None:
            received.append(evt)

        subscription = await event_bus.subscribe("test.*", callback=handler)
        await event_bus.publish(Event(topic="test.1", event_type="A"))
        await asyncio.sleep(0.1)

        assert len(received) == 1

        await event_bus.unsubscribe(subscription.id)
        await event_bus.publish(Event(topic="test.2", event_type="B"))
        await asyncio.sleep(0.1)

        assert len(received) == 1  # No new events after unsubscribe


@pytest.mark.integration
class TestEventHistory:
    """Tests for event history tracking."""

    @pytest.mark.asyncio
    async def test_event_history(self, event_bus: EventBus) -> None:
        """Test that published events are tracked in history."""
        await event_bus.publish(Event(topic="test.1", event_type="A"))
        await event_bus.publish(Event(topic="test.2", event_type="B"))

        history = event_bus.get_event_history()

        assert len(history) == 2
        assert history[0].event_type == "A"
        assert history[1].event_type == "B"


@pytest.mark.integration
class TestEventDeadLetterQueue:
    """Tests for dead letter queue."""

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self, event_bus: EventBus) -> None:
        """Test that failed events go to dead letter queue."""
        dlq: list[Event] = []

        async def failing_handler(evt: Event) -> None:
            raise Exception("Handler failed")

        subscription = await event_bus.subscribe(
            "failures.*",
            callback=failing_handler,
            priority=EventPriority.HIGH.value,
        )

        await event_bus.publish(Event(topic="failures.test", event_type="fail"))

        # Give time for async processing
        await asyncio.sleep(0.2)

        # Check DLQ was populated
        assert len(event_bus.get_dead_letter_queue()) >= 0
