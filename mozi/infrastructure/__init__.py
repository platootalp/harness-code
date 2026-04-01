"""Infrastructure module.

This module provides foundational components for the Mozi system:
- database: SQLite-based session storage
- vector_db: Vector store abstraction with multiple backends
- event_bus: Async event bus with pub/sub pattern
"""

from __future__ import annotations

from mozi.infrastructure.database import (
    Message,
    MessageRole,
    Session,
    SessionStatus,
    SQLiteSessionStorage,
)
from mozi.infrastructure.event_bus import (
    BaseEventBus,
    DeliveryMode,
    Event,
    EventBus,
    EventPriority,
    Subscription,
    SubscriptionNotFoundError,
    TopicMatcher,
)
from mozi.infrastructure.vector_db import (
    FileVectorStore,
    MemoryBlock,
    MemoryType,
    MilvusVectorStore,
    PGVectorStore,
    VectorStore,
)

__all__ = [
    # database
    "SQLiteSessionStorage",
    "Session",
    "SessionStatus",
    "Message",
    "MessageRole",
    # vector_db
    "VectorStore",
    "MemoryBlock",
    "MemoryType",
    "MilvusVectorStore",
    "PGVectorStore",
    "FileVectorStore",
    # event_bus
    "EventBus",
    "BaseEventBus",
    "Event",
    "EventPriority",
    "DeliveryMode",
    "Subscription",
    "TopicMatcher",
    "SubscriptionNotFoundError",
]
