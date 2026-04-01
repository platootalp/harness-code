"""Integration tests for Session module.

Tests session resume, streaming output persistence, and concurrent access.
"""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import timedelta
from pathlib import Path

import pytest

from mozi.session.database import SQLiteSessionStorage
from mozi.session.manager import SessionManager
from mozi.session.models import MessageRole, Session, SessionStatus


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_integration.db")


@pytest.fixture
async def session_manager(
    temp_db_path: str,
) -> AsyncGenerator[SessionManager, None]:
    """Create a test session manager."""
    storage = SQLiteSessionStorage(db_path=temp_db_path)
    mgr = SessionManager(storage)
    await mgr.init()
    yield mgr
    await mgr.close()


class TestSessionResume:
    """Tests for session resume functionality."""

    async def test_resume_nonexistent_session(
        self, session_manager: SessionManager
    ) -> None:
        """Test resuming a session that doesn't exist."""
        session = await session_manager.get_session("nonexistent-id")
        assert session is None

    async def test_resume_existing_session(
        self, session_manager: SessionManager
    ) -> None:
        """Test resuming an existing session."""
        # Create a session
        await session_manager.create_session(
            session_id="test-session",
            name="Test Session",
        )

        # Add a message
        await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello, world!",
        )

        # Resume the session
        resumed = await session_manager.get_session("test-session")
        assert resumed is not None
        assert resumed.id == "test-session"
        assert resumed.name == "Test Session"

    async def test_resume_shows_last_message(
        self, session_manager: SessionManager
    ) -> None:
        """Test that resuming shows the last message."""
        # Create a session with messages
        await session_manager.create_session(session_id="test-session")
        await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.USER,
            content="First message",
        )
        await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="Second message",
        )

        # Get messages
        messages = await session_manager.get_messages("test-session")
        assert len(messages) == 2
        assert messages[-1].content == "Second message"


class TestStreamingOutputPersistence:
    """Tests for streaming output persistence."""

    async def test_streaming_content_saved(
        self, session_manager: SessionManager
    ) -> None:
        """Test that streaming content is saved progressively."""
        # Create session and message
        await session_manager.create_session(session_id="test-session")
        msg = await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="",
            streaming_content="Starting...",
        )
        assert msg is not None
        assert msg.streaming_content == "Starting..."

        # Update with more streaming content
        await session_manager.update_message(
            message_id=msg.id,
            streaming_content="Starting... more content",
        )

        # Verify persistence
        messages = await session_manager.get_messages("test-session")
        assert len(messages) == 1
        assert messages[0].streaming_content == "Starting... more content"

    async def test_streaming_complete_after_full_content(
        self, session_manager: SessionManager
    ) -> None:
        """Test that streaming content is replaced when streaming completes."""
        # Create session and message with streaming content
        await session_manager.create_session(session_id="test-session")
        msg = await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="",
            streaming_content="Generating...",
        )

        # Simulate streaming completion - update with new streaming content
        await session_manager.update_message(
            message_id=msg.id,
            content="Final complete response",
            streaming_content="Final complete response",
        )

        # Verify final state
        messages = await session_manager.get_messages("test-session")
        assert len(messages) == 1
        assert messages[0].content == "Final complete response"
        # Note: streaming_content still holds the old value since we don't
        # automatically clear it. The content field is what matters.

    async def test_crash_recovery_scenario(
        self, session_manager: SessionManager
    ) -> None:
        """Test recovery scenario where streaming was in progress."""
        # Create session with partial streaming message
        await session_manager.create_session(session_id="test-session")
        msg = await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="",
            streaming_content="Partially generated res",
        )

        # Simulate crash - message was saved with streaming content
        # but content was not yet complete

        # On recovery, check the message state
        messages = await session_manager.get_messages("test-session")
        assert len(messages) == 1
        assert messages[0].streaming_content == "Partially generated res"
        assert messages[0].content == ""

        # Continue from where we left off
        await session_manager.update_message(
            message_id=msg.id,
            content="Partially generated response was interrupted",
        )

        messages = await session_manager.get_messages("test-session")
        assert messages[0].content == "Partially generated response was interrupted"


class TestConcurrentSessions:
    """Tests for concurrent session access."""

    async def test_concurrent_session_creation(
        self, session_manager: SessionManager
    ) -> None:
        """Test creating multiple sessions concurrently."""
        async def create_session(i: int) -> Session:
            return await session_manager.create_session(
                session_id=f"concurrent-session-{i}",
                name=f"Session {i}",
            )

        # Create 10 sessions concurrently
        sessions = await asyncio.gather(
            *[create_session(i) for i in range(10)]
        )

        assert len(sessions) == 10
        # Verify all were created
        for i in range(10):
            session = await session_manager.get_session(f"concurrent-session-{i}")
            assert session is not None
            assert session.name == f"Session {i}"

    async def test_concurrent_message_addition(
        self, session_manager: SessionManager
    ) -> None:
        """Test adding messages to different sessions concurrently."""
        # Create multiple sessions
        for i in range(5):
            await session_manager.create_session(
                session_id=f"session-{i}",
                name=f"Session {i}",
            )

        async def add_messages(session_id: str, msg_count: int) -> None:
            for j in range(msg_count):
                await session_manager.add_message(
                    session_id=session_id,
                    role=MessageRole.USER,
                    content=f"Message {j} for {session_id}",
                )

        # Add messages concurrently to all sessions
        await asyncio.gather(
            *[add_messages(f"session-{i}", 5) for i in range(5)]
        )

        # Verify each session has correct message count
        for i in range(5):
            messages = await session_manager.get_messages(f"session-{i}")
            assert len(messages) == 5

    async def test_session_isolation(
        self, session_manager: SessionManager
    ) -> None:
        """Test that sessions are properly isolated."""
        # Create two separate sessions
        await session_manager.create_session(session_id="session-a")
        await session_manager.create_session(session_id="session-b")

        # Add different messages to each
        await session_manager.add_message(
            session_id="session-a",
            role=MessageRole.USER,
            content="Message for A",
        )
        await session_manager.add_message(
            session_id="session-b",
            role=MessageRole.USER,
            content="Message for B",
        )

        # Verify isolation
        messages_a = await session_manager.get_messages("session-a")
        messages_b = await session_manager.get_messages("session-b")

        assert len(messages_a) == 1
        assert len(messages_b) == 1
        assert messages_a[0].content == "Message for A"
        assert messages_b[0].content == "Message for B"


class TestSessionLifecycle:
    """Tests for session lifecycle state transitions."""

    async def test_idle_timeout_transition(
        self, session_manager: SessionManager
    ) -> None:
        """Test automatic transition to IDLE after timeout."""
        # Create session with very short idle timeout
        storage = session_manager._storage
        short_timeout_manager = SessionManager(
            storage,
            idle_timeout=timedelta(milliseconds=10),
        )
        await short_timeout_manager.init()

        await short_timeout_manager.create_session(session_id="idle-test")
        session = await short_timeout_manager.get_session("idle-test")
        assert session is not None
        assert session.status == SessionStatus.ACTIVE

        # Wait for idle timeout
        await asyncio.sleep(0.05)

        # Session should transition to IDLE
        session = await short_timeout_manager.get_session("idle-test")
        assert session is not None
        assert session.status == SessionStatus.IDLE

        await short_timeout_manager.close()

    async def test_reactivate_from_idle(
        self, session_manager: SessionManager
    ) -> None:
        """Test reactivating an IDLE session."""
        await session_manager.create_session(session_id="test-session")

        # Manually transition to IDLE
        session = await session_manager.get_session("test-session")
        assert session is not None
        session.transition_to(SessionStatus.IDLE)
        await session_manager.update_session(
            session_id="test-session",
            status=SessionStatus.IDLE,
        )

        # Verify IDLE
        session = await session_manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.IDLE

        # Add message to reactivate
        await session_manager.add_message(
            session_id="test-session",
            role=MessageRole.USER,
            content="Reactivating message",
        )

        # Verify ACTIVE again
        session = await session_manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.ACTIVE

    async def test_archive_workflow(
        self, session_manager: SessionManager
    ) -> None:
        """Test archiving a session."""
        await session_manager.create_session(session_id="test-session")

        # Transition to IDLE first
        await session_manager.update_session(
            session_id="test-session",
            status=SessionStatus.IDLE,
        )

        # Archive
        result = await session_manager.archive_session("test-session")
        assert result is True

        session = await session_manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.ARCHIVED

    async def test_cannot_archive_active_session(
        self, session_manager: SessionManager
    ) -> None:
        """Test that active sessions cannot be directly archived."""
        await session_manager.create_session(session_id="test-session")

        result = await session_manager.archive_session("test-session")
        assert result is False

        # Session should still be ACTIVE
        session = await session_manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.ACTIVE
