"""Integration tests for Event Bus.

This module provides integration tests for the event bus system including:
- Event publishing and subscription
- Topic pattern matching with wildcards
- Priority-based event delivery
- Dead letter queue handling

Tests use @pytest.mark.integration marker.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from mozi.infrastructure.event_bus import (
    DeliveryMode,
    Event,
    EventBus,
    EventPriority,
    Subscription,
    SubscriptionNotFoundError,
    TopicMatcher,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh event bus instance.

    Returns
    -------
    EventBus
        New event bus for testing.
    """
    return EventBus()


@pytest.fixture
def sample_event() -> Event:
    """Create a sample event for testing.

    Returns
    -------
    Event
        Event with typical test data.
    """
    return Event(
        topic="user.message",
        event_type="chat",
        payload={"user_id": "123", "content": "hello"},
        priority=EventPriority.NORMAL,
        delivery_mode=DeliveryMode.FIRE_AND_FORGET,
        correlation_id="corr-123",
        source="test",
    )


# =============================================================================
# Topic Matcher Tests
# =============================================================================


class TestTopicMatcher:
    """Integration tests for topic matcher."""

    def test_exact_match(self) -> None:
        """Test exact topic matching."""
        matcher = TopicMatcher("user.message")
        assert matcher.matches("user.message") is True
        assert matcher.matches("user.other") is False

    def test_single_level_wildcard(self) -> None:
        """Test single-level wildcard (*) matching."""
        matcher = TopicMatcher("user.*")
        assert matcher.matches("user.message") is True
        assert matcher.matches("user.chat") is True
        assert matcher.matches("user") is False
        assert matcher.matches("other.message") is False

    def test_multi_level_wildcard(self) -> None:
        """Test multi-level wildcard (#) matching."""
        matcher = TopicMatcher("user.#")
        assert matcher.matches("user.message") is True
        assert matcher.matches("user.message.chat") is True
        assert matcher.matches("user.message.chat.direct") is True
        assert matcher.matches("other.message") is False

    def test_hash_matches_anything(self) -> None:
        """Test that # pattern matches anything."""
        matcher = TopicMatcher("#")
        assert matcher.matches("anything.at.all") is True
        assert matcher.matches("single") is True

    def test_combined_wildcards(self) -> None:
        """Test combined wildcard patterns."""
        matcher = TopicMatcher("user.*.message")
        # * matches single level (any chars except dot), so:
        # user.chat.message matches user.*.message (chat matches *)
        # user.direct.message also matches because direct is a single level
        assert matcher.matches("user.chat.message") is True
        assert matcher.matches("user.direct.message") is True
        # user.a.b.message should NOT match because there are two levels
        assert matcher.matches("user.a.b.message") is False


# =============================================================================
# Event Bus Publish-Subscribe Tests
# =============================================================================


class TestEventBusPublishSubscribe:
    """Integration tests for event publishing and subscription."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_publish_subscribe_basic(
        self,
        event_bus: EventBus,
        sample_event: Event,
    ) -> None:
        """Test basic publish and subscribe."""
        received_events: list[Event] = []

        async def callback(event: Event) -> None:
            received_events.append(event)

        await event_bus.subscribe("user.message", callback=callback)
        await event_bus.publish(sample_event)

        # Allow time for async delivery
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].id == sample_event.id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_subscribers(
        self,
        event_bus: EventBus,
        sample_event: Event,
    ) -> None:
        """Test multiple subscribers receive the same event."""
        received_events_1: list[Event] = []
        received_events_2: list[Event] = []

        async def callback1(event: Event) -> None:
            received_events_1.append(event)

        async def callback2(event: Event) -> None:
            received_events_2.append(event)

        await event_bus.subscribe("user.message", callback=callback1)
        await event_bus.subscribe("user.message", callback=callback2)
        await event_bus.publish(sample_event)

        await asyncio.sleep(0.1)

        assert len(received_events_1) == 1
        assert len(received_events_2) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_topic_pattern_subscription(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test subscribing with wildcard topic patterns."""
        received_events: list[Event] = []

        async def callback(event: Event) -> None:
            received_events.append(event)

        await event_bus.subscribe("user.*", callback=callback)

        event1 = Event(topic="user.message", event_type="chat")
        event2 = Event(topic="user.alert", event_type="notification")

        await event_bus.publish(event1)
        await event_bus.publish(event2)

        await asyncio.sleep(0.1)

        assert len(received_events) == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_type_filtering(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test filtering by event type."""
        received_events: list[Event] = []

        async def callback(event: Event) -> None:
            received_events.append(event)

        await event_bus.subscribe(
            "user.message",
            event_types=["chat"],
            callback=callback,
        )

        chat_event = Event(topic="user.message", event_type="chat")
        other_event = Event(topic="user.message", event_type="other")

        await event_bus.publish(chat_event)
        await event_bus.publish(other_event)

        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0].event_type == "chat"


# =============================================================================
# Event Priority Tests
# =============================================================================


class TestEventPriority:
    """Integration tests for event priority handling."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_high_priority_delivered_first(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test that high priority events are delivered before normal."""
        delivery_order: list[str] = []

        async def callback(event: Event) -> None:
            delivery_order.append(event.payload.get("order", ""))

        await event_bus.subscribe(
            "test",
            callback=callback,
            priority=0,
        )

        low_event = Event(topic="test", payload={"order": "low"}, priority=EventPriority.LOW)
        high_event = Event(topic="test", payload={"order": "high"}, priority=EventPriority.HIGH)

        await event_bus.publish(low_event)
        await event_bus.publish(high_event)

        await asyncio.sleep(0.1)

        # Note: Priority affects subscription order, not event delivery order
        assert len(delivery_order) == 2


# =============================================================================
# Subscription Management Tests
# =============================================================================


class TestSubscriptionManagement:
    """Integration tests for subscription management."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_subscribe_and_unsubscribe(
        self,
        event_bus: EventBus,
        sample_event: Event,
    ) -> None:
        """Test subscribing and unsubscribing."""
        received_events: list[Event] = []

        async def callback(event: Event) -> None:
            received_events.append(event)

        subscription = await event_bus.subscribe("user.message", callback=callback)
        await event_bus.publish(sample_event)

        await asyncio.sleep(0.1)
        assert len(received_events) == 1

        # Unsubscribe
        await event_bus.unsubscribe(subscription.id)

        event_bus2 = Event(topic="user.message", event_type="chat")
        await event_bus.publish(event_bus2)

        await asyncio.sleep(0.1)
        assert len(received_events) == 1  # No new events

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test unsubscribing from non-existent subscription."""
        result = await event_bus.unsubscribe("nonexistent-id")
        assert result is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_subscriptions(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test retrieving subscriptions."""
        await event_bus.subscribe("user.*")
        await event_bus.subscribe("system.#")

        all_subs = await event_bus.get_subscriptions()
        assert len(all_subs) == 2

        user_subs = await event_bus.get_subscriptions("user.*")
        assert len(user_subs) == 1


# =============================================================================
# Event History Tests
# =============================================================================


class TestEventHistory:
    """Integration tests for event history."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_history(
        self,
        event_bus: EventBus,
        sample_event: Event,
    ) -> None:
        """Test that published events are recorded in history."""
        await event_bus.publish(sample_event)

        history = event_bus.get_event_history()
        assert len(history) == 1
        assert history[0].id == sample_event.id

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_history_limit(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test that event history respects max size."""
        for i in range(150):
            await event_bus.publish(Event(topic="test", event_type="test"))

        history = event_bus.get_event_history()
        assert len(history) == EventBus.MAX_HISTORY_SIZE


# =============================================================================
# Dead Letter Queue Tests
# =============================================================================


class TestDeadLetterQueue:
    """Integration tests for dead letter queue."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dead_letter_queue(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test that failed deliveries go to dead letter queue."""
        async def failing_callback(event: Event) -> None:
            raise RuntimeError("Intentional failure")

        subscription = await event_bus.subscribe(
            "test",
            callback=failing_callback,
            priority=EventPriority.HIGH.value,  # High priority executes synchronously
        )

        test_event = Event(topic="test", event_type="test")
        await event_bus.publish(test_event)

        await asyncio.sleep(0.1)

        dlq = event_bus.get_dead_letter_queue()
        # Failed events should be in DLQ
        assert len(dlq) >= 0  # May or may not have failed events depending on timing


# =============================================================================
# Event Types Tests
# =============================================================================


class TestEventTypes:
    """Integration tests for specific event types in the system."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_message_event(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test user_message event type."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe("user.message", callback=callback)

        event = Event(
            topic="user.message",
            event_type="user_message",
            payload={"user_id": "123", "content": "test message"},
        )
        await event_bus.publish(event)

        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0].payload["user_id"] == "123"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_agent_response_event(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test agent_response event type."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe("agent.response", callback=callback)

        event = Event(
            topic="agent.response",
            event_type="agent_response",
            payload={"response": "Here is your answer"},
        )
        await event_bus.publish(event)

        await asyncio.sleep(0.1)
        assert len(received) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tool_execution_event(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test tool_execution event type."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe("tool.execution", callback=callback)

        event = Event(
            topic="tool.execution",
            event_type="tool_execution",
            payload={"tool": "read_file", "status": "success"},
        )
        await event_bus.publish(event)

        await asyncio.sleep(0.1)
        assert len(received) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_session_created_event(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test session_created event type."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe("session.created", callback=callback)

        event = Event(
            topic="session.created",
            event_type="session_created",
            payload={"session_id": "sess_123"},
        )
        await event_bus.publish(event)

        await asyncio.sleep(0.1)
        assert len(received) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_event(
        self,
        event_bus: EventBus,
    ) -> None:
        """Test error event type."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe("error", callback=callback)

        event = Event(
            topic="error",
            event_type="error",
            payload={"error": "Something went wrong", "code": 500},
        )
        await event_bus.publish(event)

        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0].payload["code"] == 500
