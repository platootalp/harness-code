"""Session storage abstraction for Mozi.

Defines the abstract interface for session storage backends.
Implementations can use different storage backends (SQLite, PostgreSQL, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mozi.session.models import Message, Session, SessionStatus


class SessionStorage(ABC):
    """Abstract interface for session storage.

    All session storage implementations must inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    async def init(self) -> None:
        """Initialize the storage backend.

        Called when the storage is first used. Should create any necessary
        tables, connections, or resources.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the storage backend.

        Called when cleaning up. Should release any resources.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Save a session to storage.

        Args:
            session: The session to save.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_session(self, session_id: str) -> Session | None:
        """Load a session by ID.

        Args:
            session_id: The ID of the session to load.

        Returns:
            The session if found, None otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The ID of the session to delete.

        Returns:
            True if the session was deleted, False if it wasn't found.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int | None = None,
    ) -> list[Session]:
        """List sessions with optional filtering.

        Args:
            status: Filter by session status.
            limit: Maximum number of sessions to return.

        Returns:
            List of sessions matching the criteria.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_message(self, message: Message) -> None:
        """Save a message to storage.

        Args:
            message: The message to save.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_messages(self, session_id: str) -> list[Message]:
        """Load all messages for a session.

        Args:
            session_id: The ID of the session.

        Returns:
            List of messages in the session, ordered by creation time.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_message(
        self,
        message_id: str,
        content: str | None = None,
        streaming_content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a message.

        Args:
            message_id: The ID of the message to update.
            content: New content (if provided).
            streaming_content: New streaming content (if provided).
            metadata: New metadata to merge (if provided).

        Returns:
            True if the message was updated, False if it wasn't found.
        """
        raise NotImplementedError
