"""Event Bus Module.

This module implements an async event bus with pub/sub pattern for the Mozi project.
It supports topic patterns with wildcards, priority-based delivery, and dead letter queue.
"""

from __future__ import annotations

import asyncio
import re
from abc import abstractmethod
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from mozi.exceptions import EventBusError


class EventPriority(Enum):
    """Event priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class DeliveryMode(Enum):
    """Event delivery modes."""

    FIRE_AND_FORGET = "fire_and_forget"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


@dataclass
class Event:
    """Event data class.

    Attributes:
        id: Unique event identifier.
        topic: Event topic for routing.
        event_type: Type of the event.
        payload: Event data payload.
        timestamp: Event creation timestamp.
        priority: Event priority level.
        delivery_mode: Event delivery mode.
        correlation_id: Optional correlation ID for tracing.
        source: Optional event source identifier.
        metadata: Additional event metadata.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    topic: str = ""
    event_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    delivery_mode: DeliveryMode = DeliveryMode.FIRE_AND_FORGET
    correlation_id: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Subscription:
    """Subscription data class.

    Attributes:
        id: Unique subscription identifier.
        topic_pattern: Topic pattern to match against.
        event_types: List of event types to filter.
        callback: Async callback function to invoke.
        priority: Subscription priority (higher = delivered first).
        filter_fn: Optional additional filter function.
        metadata: Additional subscription metadata.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    topic_pattern: str = ""
    event_types: list[str] = field(default_factory=list)
    callback: Callable[[Event], Awaitable[None]] | None = None
    priority: int = 0
    filter_fn: Callable[[Event], bool] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SubscriptionNotFoundError(EventBusError):
    """Raised when a subscription does not exist."""

    pass


class TopicMatcher:
    """Topic matcher with wildcard support.

    Supports:
        - Exact match: "user.message" matches "user.message"
        - Single-level wildcard (*): "user.*" matches "user.message"
        - Multi-level wildcard (#): "user.#" matches "user.message.chat"
    """

    def __init__(self, pattern: str) -> None:
        """Initialize the topic matcher.

        Args:
            pattern: Topic pattern with optional wildcards.
        """
        self.pattern = pattern
        self._regex = self._pattern_to_regex(pattern)

    def _pattern_to_regex(self, pattern: str) -> re.Pattern[str]:
        """Convert topic pattern to regex.

        Args:
            pattern: Topic pattern with * and # wildcards.

        Returns:
            Compiled regex pattern.
        """
        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace("\\#", ".*")
        regex_pattern = regex_pattern.replace("\\*", "[^.]+")
        regex_pattern = f"^{regex_pattern}$"
        return re.compile(regex_pattern)

    def matches(self, topic: str) -> bool:
        """Check if topic matches the pattern.

        Args:
            topic: Topic to check.

        Returns:
            True if topic matches the pattern, False otherwise.
        """
        if self.pattern == "#":
            return True
        if "#" not in self.pattern and "*" not in self.pattern:
            return self.pattern == topic
        return bool(self._regex.match(topic))


class BaseEventBus:
    """Abstract base class for event bus implementations."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """Publish an event.

        Args:
            event: Event to publish.
        """

    @abstractmethod
    async def subscribe(
        self,
        topic_pattern: str,
        event_types: list[str] | None = None,
        callback: Callable[[Event], Awaitable[None]] | None = None,
        priority: int = 0,
        filter_fn: Callable[[Event], bool] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Subscription:
        """Subscribe to events.

        Args:
            topic_pattern: Topic pattern to match events.
            event_types: List of event types to filter (None for all).
            callback: Async callback to invoke when event is delivered.
            priority: Subscription priority (higher = delivered first).
            filter_fn: Optional additional filter function.
            metadata: Additional subscription metadata.

        Returns:
            Subscription object.
        """

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: ID of the subscription to remove.

        Returns:
            True if unsubscribed, False if subscription not found.
        """

    @abstractmethod
    async def get_subscriptions(self, topic_pattern: str | None = None) -> list[Subscription]:
        """Get active subscriptions.

        Args:
            topic_pattern: Optional filter by topic pattern.

        Returns:
            List of matching subscriptions.
        """


class EventBus(BaseEventBus):
    """Async event bus with pub/sub pattern.

    This class implements an async event bus that supports:
        - Topic patterns with * and # wildcards
        - Priority-based event delivery
        - Event history (max 100 events)
        - Dead letter queue for failed events (max 1000)

    Attributes:
        MAX_HISTORY_SIZE: Maximum number of events to keep in history.
        MAX_DLQ_SIZE: Maximum number of events in dead letter queue.
    """

    MAX_HISTORY_SIZE: int = 100
    MAX_DLQ_SIZE: int = 1000

    def __init__(self) -> None:
        """Initialize the event bus."""
        self._subscriptions: dict[str, Subscription] = {}
        self._event_history: deque[Event] = deque(maxlen=self.MAX_HISTORY_SIZE)
        self._dead_letter_queue: deque[Event] = deque(maxlen=self.MAX_DLQ_SIZE)
        self._lock = asyncio.Lock()

    async def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers.

        Args:
            event: Event to publish.
        """
        async with self._lock:
            self._event_history.append(event)

        matching_subscriptions = await self._get_matching_subscriptions(event)

        if not matching_subscriptions:
            return

        for subscription in matching_subscriptions:
            asyncio.create_task(self._deliver_event(event, subscription))

    async def subscribe(
        self,
        topic_pattern: str,
        event_types: list[str] | None = None,
        callback: Callable[[Event], Awaitable[None]] | None = None,
        priority: int = 0,
        filter_fn: Callable[[Event], bool] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Subscription:
        """Subscribe to events.

        Args:
            topic_pattern: Topic pattern to match events.
            event_types: List of event types to filter (None for all).
            callback: Async callback to invoke when event is delivered.
            priority: Subscription priority (higher = delivered first).
            filter_fn: Optional additional filter function.
            metadata: Additional subscription metadata.

        Returns:
            Subscription object.
        """
        subscription = Subscription(
            topic_pattern=topic_pattern,
            event_types=event_types or [],
            callback=callback,
            priority=priority,
            filter_fn=filter_fn,
            metadata=metadata or {},
        )

        async with self._lock:
            self._subscriptions[subscription.id] = subscription

        return subscription

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: ID of the subscription to remove.

        Returns:
            True if unsubscribed, False if subscription not found.
        """
        async with self._lock:
            if subscription_id not in self._subscriptions:
                return False
            del self._subscriptions[subscription_id]
            return True

    async def get_subscriptions(self, topic_pattern: str | None = None) -> list[Subscription]:
        """Get active subscriptions.

        Args:
            topic_pattern: Optional filter by topic pattern.

        Returns:
            List of matching subscriptions.
        """
        async with self._lock:
            if topic_pattern is None:
                return list(self._subscriptions.values())

            matcher = TopicMatcher(topic_pattern)
            return [
                sub for sub in self._subscriptions.values()
                if matcher.matches(sub.topic_pattern)
            ]

    def get_event_history(self) -> list[Event]:
        """Get event history.

        Returns:
            List of recent events.
        """
        return list(self._event_history)

    def get_dead_letter_queue(self) -> list[Event]:
        """Get dead letter queue.

        Returns:
            List of failed events.
        """
        return list(self._dead_letter_queue)

    async def _get_matching_subscriptions(self, event: Event) -> list[Subscription]:
        """Get all subscriptions matching an event.

        Args:
            event: Event to match.

        Returns:
            List of matching subscriptions sorted by priority (descending).
        """
        async with self._lock:
            matching = []
            for subscription in self._subscriptions.values():
                matcher = TopicMatcher(subscription.topic_pattern)
                if not matcher.matches(event.topic):
                    continue

                if subscription.event_types and event.event_type not in subscription.event_types:
                    continue

                if subscription.filter_fn and not subscription.filter_fn(event):
                    continue

                matching.append(subscription)

            matching.sort(key=lambda s: s.priority, reverse=True)
            return matching

    async def _deliver_event(self, event: Event, subscription: Subscription) -> None:
        """Deliver an event to a subscription's callback.

        Args:
            event: Event to deliver.
            subscription: Subscription to deliver to.
        """
        if subscription.callback is None:
            return

        try:
            if subscription.priority >= EventPriority.HIGH.value:
                await subscription.callback(event)
            else:
                asyncio.create_task(subscription.callback(event))  # type: ignore[arg-type]
        except Exception as e:
            await self._handle_delivery_failure(event, subscription, e)

    async def _handle_delivery_failure(
        self,
        event: Event,
        subscription: Subscription,
        error: Exception,
    ) -> None:
        """Handle event delivery failure.

        Args:
            event: Event that failed to deliver.
            subscription: Subscription that failed.
            error: Exception that occurred.
        """
        event.metadata["delivery_error"] = str(error)
        event.metadata["failed_subscription_id"] = subscription.id
        self._dead_letter_queue.append(event)
