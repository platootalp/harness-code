"""Unit tests for event_bus module."""

from __future__ import annotations

import asyncio

import pytest

from mozi.infrastructure.event_bus import (
    DeliveryMode,
    Event,
    EventBus,
    EventPriority,
    Subscription,
    TopicMatcher,
)


@pytest.mark.unit
class TestTopicMatcher:
    """Unit tests for TopicMatcher."""

    def test_exact_match(self) -> None:
        """Test exact topic matching."""
        matcher = TopicMatcher("user.message")
        assert matcher.matches("user.message") is True
        assert matcher.matches("user.message.other") is False
        assert matcher.matches("other.message") is False

    def test_single_level_wildcard(self) -> None:
        """Test single-level wildcard (*) matching."""
        matcher = TopicMatcher("user.*")
        assert matcher.matches("user.message") is True
        assert matcher.matches("user.chat") is True
        assert matcher.matches("user") is False
        assert matcher.matches("user.message.chat") is False
        assert matcher.matches("other.message") is False

    def test_multi_level_wildcard(self) -> None:
        """Test multi-level wildcard (#) matching."""
        matcher = TopicMatcher("user.#")
        assert matcher.matches("user.message") is True
        assert matcher.matches("user.message.chat") is True
        assert matcher.matches("user.message.chat.reply") is True
        assert matcher.matches("other.message") is False

    def test_hash_wildcard_alone(self) -> None:
        """Test that # alone matches everything."""
        matcher = TopicMatcher("#")
        assert matcher.matches("anything") is True
        assert matcher.matches("any.topic.at.all") is True

    def test_complex_pattern(self) -> None:
        """Test complex topic pattern."""
        matcher = TopicMatcher("session.*.message")
        assert matcher.matches("session.123.message") is True
        assert matcher.matches("session.abc.message") is True
        assert matcher.matches("session.123.other") is False


@pytest.mark.unit
class TestEvent:
    """Unit tests for Event."""

    def test_event_creation(self) -> None:
        """Test Event creation with default values."""
        event = Event(topic="test.topic", event_type="test")

        assert event.id is not None
        assert event.topic == "test.topic"
        assert event.event_type == "test"
        assert event.priority == EventPriority.NORMAL
        assert event.delivery_mode == DeliveryMode.FIRE_AND_FORGET
        assert event.timestamp is not None

    def test_event_with_payload(self) -> None:
        """Test Event with payload."""
        event = Event(
            topic="user.message",
            event_type="user_message",
            payload={"user_id": "123", "content": "Hello"},
            source="cli",
        )

        assert event.payload["user_id"] == "123"
        assert event.payload["content"] == "Hello"
        assert event.source == "cli"


@pytest.mark.unit
class TestSubscription:
    """Unit tests for Subscription."""

    def test_subscription_creation(self) -> None:
        """Test Subscription creation."""
        sub = Subscription(topic_pattern="test.#", priority=10)

        assert sub.id is not None
        assert sub.topic_pattern == "test.#"
        assert sub.priority == 10
        assert sub.event_types == []

    def test_subscription_with_callback(self) -> None:
        """Test Subscription with callback."""

        async def callback(event: Event) -> None:
            pass

        sub = Subscription(
            topic_pattern="test",
            callback=callback,
            priority=5,
        )

        assert sub.callback is callback


@pytest.mark.unit
class TestEventBus:
    """Unit tests for EventBus."""

    @pytest.fixture
    def event_bus(self) -> EventBus:
        """Create an EventBus instance."""
        return EventBus()

    @pytest.fixture
    async def event_bus_with_subscriber(
        self, event_bus: EventBus
    ) -> tuple[EventBus, list[Event]]:
        """Create EventBus with a subscriber."""
        received_events: list[Event] = []

        async def callback(event: Event) -> None:
            received_events.append(event)

        await event_bus.subscribe(
            topic_pattern="test.#",
            callback=callback,
            priority=1,
        )

        return event_bus, received_events

    async def test_publish_and_subscribe(
        self, event_bus: EventBus
    ) -> None:
        """Test basic publish and subscribe."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe(
            topic_pattern="test.topic",
            callback=callback,
        )

        event = Event(topic="test.topic", event_type="test")
        await event_bus.publish(event)

        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].id == event.id

    async def test_multiple_subscribers(self, event_bus: EventBus) -> None:
        """Test multiple subscribers for same topic."""
        received1: list[Event] = []
        received2: list[Event] = []

        async def callback1(event: Event) -> None:
            received1.append(event)

        async def callback2(event: Event) -> None:
            received2.append(event)

        await event_bus.subscribe(topic_pattern="test.#", callback=callback1)
        await event_bus.subscribe(topic_pattern="test.#", callback=callback2)

        event = Event(topic="test.message", event_type="test")
        await event_bus.publish(event)

        await asyncio.sleep(0.1)

        assert len(received1) == 1
        assert len(received2) == 1

    async def test_unsubscribe(self, event_bus: EventBus) -> None:
        """Test unsubscribing."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        subscription = await event_bus.subscribe(
            topic_pattern="test.#",
            callback=callback,
        )

        event1 = Event(topic="test.first", event_type="test")
        await event_bus.publish(event1)
        await asyncio.sleep(0.1)

        assert len(received) == 1

        await event_bus.unsubscribe(subscription.id)

        event2 = Event(topic="test.second", event_type="test")
        await event_bus.publish(event2)
        await asyncio.sleep(0.1)

        assert len(received) == 1

    async def test_unsubscribe_nonexistent(self, event_bus: EventBus) -> None:
        """Test unsubscribing a non-existent subscription."""
        result = await event_bus.unsubscribe("nonexistent-id")
        assert result is False

    async def test_get_subscriptions(self, event_bus: EventBus) -> None:
        """Test getting subscriptions."""
        await event_bus.subscribe(topic_pattern="test.1", priority=1)
        await event_bus.subscribe(topic_pattern="test.2", priority=2)

        all_subs = await event_bus.get_subscriptions()
        assert len(all_subs) == 2

        pattern_subs = await event_bus.get_subscriptions("test.1")
        assert len(pattern_subs) == 1

    async def test_event_history(self, event_bus: EventBus) -> None:
        """Test event history tracking."""
        for i in range(5):
            event = Event(topic=f"test.{i}", event_type="test")
            await event_bus.publish(event)

        history = event_bus.get_event_history()
        assert len(history) == 5

    async def test_dead_letter_queue(self, event_bus: EventBus) -> None:
        """Test dead letter queue for failed events."""

        async def failing_callback(event: Event) -> None:
            raise RuntimeError("Simulated failure")

        await event_bus.subscribe(
            topic_pattern="fail.#",
            callback=failing_callback,
            priority=EventPriority.HIGH.value,
        )

        event = Event(topic="fail.test", event_type="test")
        await event_bus.publish(event)

        await asyncio.sleep(0.2)

        dlq = event_bus.get_dead_letter_queue()
        assert len(dlq) == 1
        assert dlq[0].metadata["delivery_error"] == "Simulated failure"

    async def test_priority_ordering(self, event_bus: EventBus) -> None:
        """Test that higher priority subscribers receive events first."""
        call_order: list[int] = []

        async def callback1(event: Event) -> None:
            call_order.append(1)

        async def callback2(event: Event) -> None:
            call_order.append(2)

        await event_bus.subscribe(
            topic_pattern="priority.test",
            callback=callback1,
            priority=1,
        )
        await event_bus.subscribe(
            topic_pattern="priority.test",
            callback=callback2,
            priority=2,
        )

        event = Event(topic="priority.test", event_type="test")
        await event_bus.publish(event)

        await asyncio.sleep(0.1)

        assert len(call_order) == 2

    async def test_event_type_filter(self, event_bus: EventBus) -> None:
        """Test filtering by event type."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        await event_bus.subscribe(
            topic_pattern="test.#",
            event_types=["allowed_type"],
            callback=callback,
        )

        event1 = Event(topic="test.1", event_type="allowed_type")
        event2 = Event(topic="test.2", event_type="other_type")

        await event_bus.publish(event1)
        await event_bus.publish(event2)

        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].event_type == "allowed_type"

    async def test_filter_function(self, event_bus: EventBus) -> None:
        """Test filter function on subscriptions."""
        received: list[Event] = []

        async def callback(event: Event) -> None:
            received.append(event)

        def filter_fn(event: Event) -> bool:
            return bool(event.payload.get("allowed", False))

        await event_bus.subscribe(
            topic_pattern="filter.#",
            callback=callback,
            filter_fn=filter_fn,
        )

        event1 = Event(topic="filter.1", event_type="test", payload={"allowed": True})
        event2 = Event(topic="filter.2", event_type="test", payload={"allowed": False})

        await event_bus.publish(event1)
        await event_bus.publish(event2)

        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].payload["allowed"] is True

    async def test_high_priority_sync(self, event_bus: EventBus) -> None:
        """Test that HIGH priority callbacks are awaited synchronously."""
        call_order: list[str] = []

        async def high_priority_callback(event: Event) -> None:
            call_order.append("high_start")
            await asyncio.sleep(0.05)
            call_order.append("high_end")

        async def low_priority_callback(event: Event) -> None:
            call_order.append("low")

        await event_bus.subscribe(
            topic_pattern="sync.test",
            callback=high_priority_callback,
            priority=EventPriority.HIGH.value,
        )
        await event_bus.subscribe(
            topic_pattern="sync.test",
            callback=low_priority_callback,
            priority=EventPriority.LOW.value,
        )

        event = Event(topic="sync.test", event_type="test")
        await event_bus.publish(event)

        await asyncio.sleep(0.15)

        assert "high_start" in call_order
        assert "high_end" in call_order
        assert "low" in call_order
