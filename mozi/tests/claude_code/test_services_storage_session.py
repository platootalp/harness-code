"""Tests for services/storage/session.py - SessionStorage."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from claude_code.services.storage.session import (
    SessionStorage,
    StoredSession,
)


class TestStoredSession:
    """Tests for StoredSession dataclass."""

    def test_basic_session(self) -> None:
        """Test basic session creation."""
        session = StoredSession(
            session_id="sess-123",
            environment_id="env-456",
        )
        assert session.session_id == "sess-123"
        assert session.environment_id == "env-456"
        assert session.title is None
        assert session.created_at is None
        assert session.updated_at is None
        assert session.metadata is None

    def test_session_with_metadata(self) -> None:
        """Test session with all fields."""
        session = StoredSession(
            session_id="sess-123",
            environment_id="env-456",
            title="My Session",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T01:00:00Z",
            metadata={"key": "value"},
        )
        assert session.title == "My Session"
        assert session.created_at == "2024-01-01T00:00:00Z"
        assert session.updated_at == "2024-01-01T01:00:00Z"
        assert session.metadata == {"key": "value"}

    def test_to_dict(self) -> None:
        """Test converting session to dictionary."""
        session = StoredSession(
            session_id="sess-123",
            environment_id="env-456",
            title="Test",
        )
        data = session.to_dict()
        assert data["session_id"] == "sess-123"
        assert data["environment_id"] == "env-456"
        assert data["title"] == "Test"

    def test_from_dict(self) -> None:
        """Test creating session from dictionary."""
        data = {
            "session_id": "sess-123",
            "environment_id": "env-456",
            "title": "Test",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T01:00:00Z",
            "metadata": {"foo": "bar"},
        }
        session = StoredSession.from_dict(data)
        assert session.session_id == "sess-123"
        assert session.environment_id == "env-456"
        assert session.title == "Test"
        assert session.created_at == "2024-01-01T00:00:00Z"
        assert session.updated_at == "2024-01-01T01:00:00Z"
        assert session.metadata == {"foo": "bar"}

    def test_from_dict_missing_optional(self) -> None:
        """Test from_dict with missing optional fields."""
        data = {"session_id": "sess-1", "environment_id": "env-1"}
        session = StoredSession.from_dict(data)
        assert session.session_id == "sess-1"
        assert session.title is None
        assert session.metadata is None

    def test_roundtrip(self) -> None:
        """Test session to_dict and from_dict roundtrip."""
        original = StoredSession(
            session_id="sess-123",
            environment_id="env-456",
            title="Test Session",
            metadata={"count": 42},
        )
        restored = StoredSession.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.environment_id == original.environment_id
        assert restored.title == original.title
        assert restored.metadata == original.metadata


class TestSessionStorage:
    """Tests for SessionStorage class."""

    def setup_method(self) -> None:
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = SessionStorage(storage_dir=Path(self.temp_dir))

    def teardown_method(self) -> None:
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_storage_dir(self) -> None:
        """Test default storage directory is set correctly."""
        storage = SessionStorage()
        # Should default to ~/.claude/sessions
        assert storage._storage_dir.name == "sessions"

    def test_custom_storage_dir(self) -> None:
        """Test custom storage directory is created."""
        assert self.storage._storage_dir.exists()
        assert self.storage._storage_dir.is_dir()

    def test_session_path(self) -> None:
        """Test session path generation."""
        path = self.storage._session_path("my-session")
        assert path.parent == self.storage._storage_dir
        assert path.name == "my-session.json"

    @pytest.mark.asyncio
    async def test_save_and_load(self) -> None:
        """Test saving and loading a session."""
        session = StoredSession(
            session_id="test-save-load",
            environment_id="env-1",
            title="Save Test",
        )
        await self.storage.save(session)

        loaded = await self.storage.load("test-save-load")
        assert loaded is not None
        assert loaded.session_id == "test-save-load"
        assert loaded.environment_id == "env-1"
        assert loaded.title == "Save Test"
        assert loaded.created_at is not None
        assert loaded.updated_at is not None

    @pytest.mark.asyncio
    async def test_save_updates_timestamps(self) -> None:
        """Test save updates created_at and updated_at."""
        session = StoredSession(
            session_id="ts-test",
            environment_id="env-1",
        )
        await self.storage.save(session)

        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.created_at == session.updated_at

        # Wait a bit and save again
        import time
        time.sleep(0.01)
        await self.storage.save(session)
        assert session.updated_at >= session.created_at

    @pytest.mark.asyncio
    async def test_load_nonexistent(self) -> None:
        """Test loading nonexistent session returns None."""
        result = await self.storage.load("does-not-exist")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_invalid_json(self) -> None:
        """Test loading invalid JSON returns None."""
        # Write invalid JSON
        path = self.storage._session_path("invalid-json")
        path.write_text("not valid json{{{")
        result = await self.storage.load("invalid-json")
        assert result is None

    @pytest.mark.asyncio
    async def test_load_missing_fields(self) -> None:
        """Test loading JSON with missing required fields returns None."""
        path = self.storage._session_path("missing-fields")
        path.write_text('{"session_id": "only-one"}')
        result = await self.storage.load("missing-fields")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing(self) -> None:
        """Test deleting existing session."""
        session = StoredSession(session_id="to-delete", environment_id="env-1")
        await self.storage.save(session)

        assert await self.storage.exists("to-delete")
        await self.storage.delete("to-delete")
        assert not await self.storage.exists("to-delete")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self) -> None:
        """Test deleting nonexistent session doesn't raise."""
        await self.storage.delete("never-existed")

    @pytest.mark.asyncio
    async def test_exists(self) -> None:
        """Test checking if session exists."""
        assert not await self.storage.exists("new-session")
        session = StoredSession(session_id="new-session", environment_id="env-1")
        await self.storage.save(session)
        assert await self.storage.exists("new-session")

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        """Test listing empty storage."""
        sessions = await self.storage.list()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_multiple_sessions(self) -> None:
        """Test listing multiple sessions."""
        for i in range(3):
            session = StoredSession(
                session_id=f"session-{i}",
                environment_id="env-1",
            )
            await self.storage.save(session)

        sessions = await self.storage.list()
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_list_sorted_by_updated_at(self) -> None:
        """Test sessions are sorted by updated_at descending."""
        import time

        session1 = StoredSession(session_id="older", environment_id="env-1")
        await self.storage.save(session1)

        time.sleep(0.01)
        session2 = StoredSession(session_id="newer", environment_id="env-1")
        await self.storage.save(session2)

        sessions = await self.storage.list()
        assert sessions[0].session_id == "newer"
        assert sessions[1].session_id == "older"

    @pytest.mark.asyncio
    async def test_list_skips_invalid_files(self) -> None:
        """Test list skips invalid JSON files."""
        # Write valid sessions
        for i in range(2):
            session = StoredSession(session_id=f"valid-{i}", environment_id="env-1")
            await self.storage.save(session)

        # Write invalid file
        bad_path = self.storage._session_path("bad-file")
        bad_path.write_text("not json")

        sessions = await self.storage.list()
        assert len(sessions) == 2
        assert all(s.session_id.startswith("valid-") for s in sessions)

    @pytest.mark.asyncio
    async def test_save_overwrites(self) -> None:
        """Test saving session with same ID overwrites."""
        session1 = StoredSession(
            session_id="overwrite-test",
            environment_id="env-1",
            title="Original",
        )
        await self.storage.save(session1)

        session2 = StoredSession(
            session_id="overwrite-test",
            environment_id="env-1",
            title="Updated",
        )
        await self.storage.save(session2)

        loaded = await self.storage.load("overwrite-test")
        assert loaded is not None
        assert loaded.title == "Updated"
