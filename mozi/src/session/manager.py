"""Session manager for Mozi.

Provides high-level session management with state machine logic.
Handles session creation, updates, and lifecycle transitions.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from mozi.session.models import Message, MessageRole, Session, SessionStatus
from mozi.session.storage import SessionStorage


class SessionManager:
    """High-level session management with state machine.

    Provides CRUD operations and enforces state transitions:
    - ACTIVE: Session is actively being used
    - IDLE: Session has been inactive for a while
    - ARCHIVED: Session is manually or automatically archived
    - EXPIRED: Session has been archived for too long
    """

    # Idle timeout: 30 minutes of inactivity
    DEFAULT_IDLE_TIMEOUT = timedelta(minutes=30)

    # Archive TTL: 7 days after archiving
    DEFAULT_ARCHIVE_TTL = timedelta(days=7)

    def __init__(
        self,
        storage: SessionStorage,
        idle_timeout: timedelta | None = None,
        archive_ttl: timedelta | None = None,
    ) -> None:
        """Initialize session manager.

        Args:
            storage: Session storage backend.
            idle_timeout: Timeout before ACTIVE → IDLE transition.
            archive_ttl: Time after ARCHIVED before EXPIRED transition.
        """
        self._storage = storage
        self._idle_timeout = idle_timeout or self.DEFAULT_IDLE_TIMEOUT
        self._archive_ttl = archive_ttl or self.DEFAULT_ARCHIVE_TTL

    async def init(self) -> None:
        """Initialize the storage backend."""
        await self._storage.init()

    async def close(self) -> None:
        """Close the storage backend."""
        await self._storage.close()

    async def create_session(
        self,
        session_id: str,
        name: str | None = None,
        user_id: str | None = None,
        working_dir: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            session_id: Unique identifier for the session.
            name: Optional human-readable name.
            user_id: User who owns the session.
            working_dir: Working directory for the session.
            model: Model to use for this session.
            system_prompt: System prompt configuration.
            metadata: Additional session metadata.
            tags: Tags for categorizing the session.

        Returns:
            The newly created session.
        """
        session = Session(
            id=session_id,
            name=name,
            user_id=user_id,
            status=SessionStatus.ACTIVE,
            working_dir=working_dir,
            model=model,
            system_prompt=system_prompt,
            metadata=metadata or {},
            tags=tags or [],
        )

        await self._storage.save_session(session)
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID.

        Also checks for idle timeout and archives if needed.

        Args:
            session_id: The session ID to retrieve.

        Returns:
            The session if found and valid, None otherwise.
        """
        session = await self._storage.load_session(session_id)
        if session is None:
            return None

        # Check for idle timeout
        await self._check_idle_transition(session)

        # Check for archive TTL expiration
        await self._check_archive_expiration(session)

        return session

    async def update_session(
        self,
        session_id: str,
        name: str | None = None,
        status: SessionStatus | None = None,
        working_dir: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> Session | None:
        """Update a session.

        Args:
            session_id: The session ID to update.
            name: New name (if provided).
            status: New status (if provided).
            working_dir: New working directory (if provided).
            metadata: Metadata to merge (if provided).
            tags: New tags (if provided).
            model: New model (if provided).
            system_prompt: New system prompt (if provided).

        Returns:
            The updated session if found, None otherwise.
        """
        session = await self._storage.load_session(session_id)
        if session is None:
            return None

        if name is not None:
            session.name = name
        if working_dir is not None:
            session.working_dir = working_dir
        if metadata is not None:
            session.metadata.update(metadata)
        if tags is not None:
            session.tags = tags
        if model is not None:
            session.model = model
        if system_prompt is not None:
            session.system_prompt = system_prompt

        if status is not None:
            session.transition_to(status)

        session.updated_at = datetime.utcnow()
        await self._storage.save_session(session)
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages.

        Args:
            session_id: The session ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        return await self._storage.delete_session(session_id)

    async def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int | None = None,
    ) -> list[Session]:
        """List sessions with optional filtering.

        Args:
            status: Filter by status.
            limit: Maximum number to return.

        Returns:
            List of sessions.
        """
        return await self._storage.list_sessions(status=status, limit=limit)

    async def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
        streaming_content: str | None = None,
    ) -> Message | None:
        """Add a message to a session.

        Also updates the session's last_interaction_at and
        transitions from IDLE back to ACTIVE if needed.

        Args:
            session_id: The session to add to.
            role: Message role.
            content: Message content.
            metadata: Additional metadata.
            streaming_content: Streaming content (for AI responses).

        Returns:
            The created message, or None if session not found.
        """
        session = await self._storage.load_session(session_id)
        if session is None:
            return None

        # Reactivate if IDLE
        if session.status == SessionStatus.IDLE:
            session.transition_to(SessionStatus.ACTIVE)

        message = Message(
            id=f"{session_id}-msg-{datetime.utcnow().timestamp()}",
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
            streaming_content=streaming_content,
        )

        await self._storage.save_message(message)

        # Update session
        session.last_interaction_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        await self._storage.save_session(session)

        return message

    async def update_message(
        self,
        message_id: str,
        content: str | None = None,
        streaming_content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a message's content or metadata.

        Args:
            message_id: The message ID to update.
            content: New content (if provided).
            streaming_content: New streaming content (if provided).
            metadata: Metadata to merge (if provided).

        Returns:
            True if updated, False if not found.
        """
        return await self._storage.update_message(
            message_id=message_id,
            content=content,
            streaming_content=streaming_content,
            metadata=metadata,
        )

    async def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session.

        Args:
            session_id: The session ID.

        Returns:
            List of messages ordered by creation time.
        """
        return await self._storage.load_messages(session_id)

    async def archive_session(self, session_id: str) -> bool:
        """Archive a session.

        Args:
            session_id: The session ID to archive.

        Returns:
            True if archived, False if not found.
        """
        session = await self._storage.load_session(session_id)
        if session is None:
            return False

        try:
            session.transition_to(SessionStatus.ARCHIVED)
        except ValueError:
            # Can't archive if not in IDLE state
            return False

        await self._storage.save_session(session)
        return True

    async def reactivate_session(self, session_id: str) -> bool:
        """Reactivate an archived or idle session.

        Args:
            session_id: The session ID to reactivate.

        Returns:
            True if reactivated, False if not found or can't transition.
        """
        session = await self._storage.load_session(session_id)
        if session is None:
            return False

        try:
            session.transition_to(SessionStatus.ACTIVE)
        except ValueError:
            return False

        await self._storage.save_session(session)
        return True

    async def _check_idle_transition(self, session: Session) -> None:
        """Check and perform IDLE transition if needed.

        Args:
            session: The session to check.
        """
        if session.status != SessionStatus.ACTIVE:
            return

        elapsed = datetime.utcnow() - session.last_interaction_at
        if elapsed >= self._idle_timeout:
            session.transition_to(SessionStatus.IDLE)
            await self._storage.save_session(session)

    async def _check_archive_expiration(self, session: Session) -> None:
        """Check and perform EXPIRED transition if TTL exceeded.

        Args:
            session: The session to check.
        """
        if session.status != SessionStatus.ARCHIVED:
            return

        elapsed = datetime.utcnow() - session.updated_at
        if elapsed >= self._archive_ttl:
            session.transition_to(SessionStatus.EXPIRED)
            await self._storage.save_session(session)
