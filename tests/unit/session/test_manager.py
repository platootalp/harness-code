"""Unit tests for session manager."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest

from mozi.session.database import SQLiteSessionStorage
from mozi.session.manager import SessionManager
from mozi.session.models import MessageRole, SessionStatus


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_manager.db")


@pytest.fixture
async def manager(temp_db_path: str) -> AsyncGenerator[SessionManager, None]:
    """Create a test session manager."""
    storage = SQLiteSessionStorage(db_path=temp_db_path)
    mgr = SessionManager(storage)
    await mgr.init()
    yield mgr
    await mgr.close()


class TestSessionManager:
    """Unit tests for SessionManager."""

    async def test_create_session(self, manager: SessionManager) -> None:
        """Test creating a new session."""
        session = await manager.create_session(
            session_id="test-session",
            name="My Test Session",
            user_id="user-123",
            working_dir="/test/path",
        )

        assert session.id == "test-session"
        assert session.name == "My Test Session"
        assert session.user_id == "user-123"
        assert session.working_dir == "/test/path"
        assert session.status == SessionStatus.ACTIVE

    async def test_get_session(self, manager: SessionManager) -> None:
        """Test getting a session by ID."""
        await manager.create_session(session_id="test-session")
        session = await manager.get_session("test-session")

        assert session is not None
        assert session.id == "test-session"

    async def test_get_nonexistent_session(self, manager: SessionManager) -> None:
        """Test getting a session that doesn't exist."""
        session = await manager.get_session("nonexistent")
        assert session is None

    async def test_update_session(self, manager: SessionManager) -> None:
        """Test updating a session."""
        await manager.create_session(session_id="test-session")

        session = await manager.update_session(
            session_id="test-session",
            name="Updated Name",
            metadata={"new_key": "new_value"},
        )

        assert session is not None
        assert session.name == "Updated Name"
        assert session.metadata["new_key"] == "new_value"

    async def test_update_nonexistent_session(self, manager: SessionManager) -> None:
        """Test updating a session that doesn't exist."""
        session = await manager.update_session(
            session_id="nonexistent",
            name="New Name",
        )
        assert session is None

    async def test_delete_session(self, manager: SessionManager) -> None:
        """Test deleting a session."""
        await manager.create_session(session_id="test-session")

        result = await manager.delete_session("test-session")
        assert result is True

        session = await manager.get_session("test-session")
        assert session is None

    async def test_delete_nonexistent_session(self, manager: SessionManager) -> None:
        """Test deleting a session that doesn't exist."""
        result = await manager.delete_session("nonexistent")
        assert result is False

    async def test_list_sessions(self, manager: SessionManager) -> None:
        """Test listing sessions."""
        for i in range(5):
            await manager.create_session(session_id=f"test-session-{i}")

        sessions = await manager.list_sessions()
        assert len(sessions) >= 5

    async def test_list_sessions_with_status(self, manager: SessionManager) -> None:
        """Test listing sessions filtered by status."""
        await manager.create_session(session_id="active-session")
        await manager.create_session(session_id="idle-session")
        await manager.update_session(
            session_id="idle-session", status=SessionStatus.IDLE
        )

        active_sessions = await manager.list_sessions(status=SessionStatus.ACTIVE)
        assert all(s.status == SessionStatus.ACTIVE for s in active_sessions)

        idle_sessions = await manager.list_sessions(status=SessionStatus.IDLE)
        assert all(s.status == SessionStatus.IDLE for s in idle_sessions)

    async def test_add_message(self, manager: SessionManager) -> None:
        """Test adding a message to a session."""
        await manager.create_session(session_id="test-session")

        message = await manager.add_message(
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello, world!",
        )

        assert message is not None
        assert message.content == "Hello, world!"
        assert message.role == MessageRole.USER

    async def test_add_message_to_nonexistent_session(
        self, manager: SessionManager
    ) -> None:
        """Test adding a message to a session that doesn't exist."""
        message = await manager.add_message(
            session_id="nonexistent",
            role=MessageRole.USER,
            content="Hello!",
        )
        assert message is None

    async def test_get_messages(self, manager: SessionManager) -> None:
        """Test getting messages for a session."""
        await manager.create_session(session_id="test-session")

        await manager.add_message(
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello!",
        )
        await manager.add_message(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="Hi there!",
        )

        messages = await manager.get_messages("test-session")
        assert len(messages) == 2
        assert messages[0].role == MessageRole.USER
        assert messages[1].role == MessageRole.ASSISTANT

    async def test_update_message(self, manager: SessionManager) -> None:
        """Test updating a message."""
        await manager.create_session(session_id="test-session")

        message = await manager.add_message(
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="Initial content",
        )
        assert message is not None

        result = await manager.update_message(
            message_id=message.id,
            content="Updated content",
            streaming_content="Streaming...",
        )
        assert result is True

    async def test_archive_session(self, manager: SessionManager) -> None:
        """Test archiving a session."""
        await manager.create_session(session_id="test-session")

        # Transition to IDLE first (required before archiving)
        await manager.update_session(
            session_id="test-session", status=SessionStatus.IDLE
        )

        result = await manager.archive_session("test-session")
        assert result is True

        session = await manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.ARCHIVED

    async def test_archive_active_session_fails(self, manager: SessionManager) -> None:
        """Test that archiving an ACTIVE session fails."""
        await manager.create_session(session_id="test-session")

        result = await manager.archive_session("test-session")
        assert result is False

    async def test_reactivate_session(self, manager: SessionManager) -> None:
        """Test reactivating an archived session."""
        await manager.create_session(session_id="test-session")
        await manager.update_session(
            session_id="test-session", status=SessionStatus.IDLE
        )
        await manager.archive_session("test-session")

        result = await manager.reactivate_session("test-session")
        assert result is True

        session = await manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.ACTIVE

    async def test_idle_to_active_transition_on_message(
        self, manager: SessionManager
    ) -> None:
        """Test that adding a message reactivates an IDLE session."""
        await manager.create_session(session_id="test-session")
        await manager.update_session(
            session_id="test-session", status=SessionStatus.IDLE
        )

        await manager.add_message(
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello!",
        )

        session = await manager.get_session("test-session")
        assert session is not None
        assert session.status == SessionStatus.ACTIVE
