"""Unit tests for session storage implementations."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest

from mozi.session.database import SQLiteSessionStorage
from mozi.session.models import Message, MessageRole, Session, SessionStatus


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield str(Path(tmpdir) / "test_sessions.db")


@pytest.fixture
async def storage(temp_db_path: str) -> AsyncGenerator[SQLiteSessionStorage, None]:
    """Create and initialize a test storage instance."""
    storage = SQLiteSessionStorage(db_path=temp_db_path)
    await storage.init()
    yield storage
    await storage.close()


@pytest.fixture
async def storage_with_session(
    temp_db_path: str,
) -> AsyncGenerator[tuple[SQLiteSessionStorage, Session], None]:
    """Create storage with a pre-created session."""
    storage = SQLiteSessionStorage(db_path=temp_db_path)
    await storage.init()

    session = Session(
        id="test-session-1",
        name="Test Session",
        user_id="user-123",
        working_dir="/test/path",
        status=SessionStatus.ACTIVE,
        metadata={"key": "value"},
        tags=["test", "unit"],
    )
    await storage.save_session(session)

    yield storage, session
    await storage.close()


class TestSQLiteSessionStorage:
    """Unit tests for SQLiteSessionStorage."""

    async def test_init_creates_tables(self, temp_db_path: str) -> None:
        """Test that init() creates required tables."""
        storage = SQLiteSessionStorage(db_path=temp_db_path)
        await storage.init()

        db = await storage._ensure_db()
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cursor:
            tables = [row[0] for row in await cursor.fetchall()]

        assert "sessions" in tables
        assert "messages" in tables
        assert "artifacts" in tables
        await storage.close()

    async def test_save_and_load_session(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test saving and loading a session."""
        session = Session(
            id="test-session-1",
            name="Test Session",
            user_id="user-123",
            working_dir="/test/path",
            status=SessionStatus.ACTIVE,
            metadata={"key": "value"},
            tags=["test", "unit"],
        )

        await storage.save_session(session)
        loaded = await storage.load_session("test-session-1")

        assert loaded is not None
        assert loaded.id == session.id
        assert loaded.name == session.name
        assert loaded.user_id == session.user_id
        assert loaded.working_dir == session.working_dir
        assert loaded.status == session.status
        assert loaded.metadata == session.metadata
        assert loaded.tags == session.tags

    async def test_load_nonexistent_session(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test loading a session that doesn't exist."""
        result = await storage.load_session("nonexistent-id")
        assert result is None

    async def test_delete_session(self, storage: SQLiteSessionStorage) -> None:
        """Test deleting a session."""
        session = Session(id="delete-test-session")
        await storage.save_session(session)

        result = await storage.delete_session("delete-test-session")
        assert result is True

        loaded = await storage.load_session("delete-test-session")
        assert loaded is None

    async def test_delete_nonexistent_session(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test deleting a session that doesn't exist."""
        result = await storage.delete_session("nonexistent-id")
        assert result is False

    async def test_list_sessions(self, storage: SQLiteSessionStorage) -> None:
        """Test listing sessions."""
        for i in range(5):
            session = Session(
                id=f"list-test-session-{i}",
                status=SessionStatus.ACTIVE if i % 2 == 0 else SessionStatus.IDLE,
            )
            await storage.save_session(session)

        all_sessions = await storage.list_sessions()
        assert len(all_sessions) >= 5

        active_sessions = await storage.list_sessions(status=SessionStatus.ACTIVE)
        for session in active_sessions:
            assert session.status == SessionStatus.ACTIVE

    async def test_list_sessions_with_limit(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test listing sessions with a limit."""
        for i in range(10):
            session = Session(id=f"limit-test-session-{i}")
            await storage.save_session(session)

        sessions = await storage.list_sessions(limit=5)
        assert len(sessions) == 5

    async def test_save_and_load_message(
        self, storage_with_session: tuple[SQLiteSessionStorage, Session]
    ) -> None:
        """Test saving and loading a message."""
        storage, session = storage_with_session

        message = Message(
            id="test-message-1",
            session_id=session.id,
            role=MessageRole.USER,
            content="Hello, world!",
            metadata={"source": "test"},
        )

        await storage.save_message(message)
        messages = await storage.load_messages(session.id)

        assert len(messages) == 1
        assert messages[0].id == message.id
        assert messages[0].role == message.role
        assert messages[0].content == message.content
        assert messages[0].metadata == message.metadata

    async def test_load_messages_empty(
        self, storage_with_session: tuple[SQLiteSessionStorage, Session]
    ) -> None:
        """Test loading messages for a session with no messages."""
        storage, session = storage_with_session

        messages = await storage.load_messages(session.id)
        assert len(messages) == 0

    async def test_large_message_stored_as_artifact(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test that large messages are stored as artifacts."""
        session = Session(id="large-msg-session")
        await storage.save_session(session)

        large_content = "x" * (20 * 1024)  # 20KB
        message = Message(
            id="large-message",
            session_id="large-msg-session",
            role=MessageRole.ASSISTANT,
            content=large_content,
        )

        await storage.save_message(message)
        messages = await storage.load_messages("large-msg-session")

        assert len(messages) == 1
        assert messages[0].content == large_content

    async def test_update_message(
        self, storage_with_session: tuple[SQLiteSessionStorage, Session]
    ) -> None:
        """Test updating a message."""
        storage, session = storage_with_session

        message = Message(
            id="update-test-msg",
            session_id=session.id,
            role=MessageRole.USER,
            content="Original content",
        )
        await storage.save_message(message)

        result = await storage.update_message(
            message_id="update-test-msg",
            content="Updated content",
            streaming_content="Streaming...",
        )

        assert result is True
        messages = await storage.load_messages(session.id)
        assert len(messages) == 1
        assert messages[0].content == "Updated content"
        assert messages[0].streaming_content == "Streaming..."

    async def test_update_nonexistent_message(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test updating a message that doesn't exist."""
        result = await storage.update_message(
            message_id="nonexistent-msg",
            content="New content",
        )
        assert result is False

    async def test_context_manager(self, temp_db_path: str) -> None:
        """Test using storage as async context manager."""
        async with SQLiteSessionStorage(db_path=temp_db_path) as storage:
            session = Session(id="ctx-test-session")
            await storage.save_session(session)

        async with SQLiteSessionStorage(db_path=temp_db_path) as storage:
            loaded = await storage.load_session("ctx-test-session")
            assert loaded is not None

    async def test_update_session(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test updating an existing session."""
        session = Session(id="update-test-session", name="Original Name")
        await storage.save_session(session)

        session.name = "Updated Name"
        session.metadata = {"updated": True}
        await storage.save_session(session)

        loaded = await storage.load_session("update-test-session")
        assert loaded is not None
        assert loaded.name == "Updated Name"
        assert loaded.metadata == {"updated": True}

    async def test_session_status_transitions(
        self, storage: SQLiteSessionStorage
    ) -> None:
        """Test session status transitions."""
        session = Session(id="status-test-session", status=SessionStatus.ACTIVE)
        await storage.save_session(session)

        session.status = SessionStatus.IDLE
        await storage.save_session(session)

        loaded = await storage.load_session("status-test-session")
        assert loaded is not None
        assert loaded.status == SessionStatus.IDLE
