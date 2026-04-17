"""Tests for models/session.py."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from claude_code.models.session import (
    AppState,
    Session,
    _parse_datetime,
)

# =============================================================================
# Session Tests
# =============================================================================


class TestSession:
    def test_default_creation(self) -> None:
        """Session should be created with default values."""
        session = Session()
        assert isinstance(session.id, UUID)
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert session.messages == []
        assert session.context == {}
        assert session.metadata == {}

    def test_creation_with_values(self) -> None:
        """Session should accept custom values."""
        session_id = uuid4()
        now = datetime.utcnow()
        session = Session(
            id=session_id,
            created_at=now,
            updated_at=now,
            messages=[{"role": "user", "content": "hello"}],
            context={"key": "value"},
            metadata={"tag": "test"},
        )
        assert session.id == session_id
        assert session.created_at == now
        assert session.updated_at == now
        assert session.messages == [{"role": "user", "content": "hello"}]
        assert session.context == {"key": "value"}
        assert session.metadata == {"tag": "test"}

    def test_to_dict(self) -> None:
        """Session.to_dict should serialize all fields."""
        session_id = uuid4()
        now = datetime(2026, 1, 1, 12, 0, 0)
        session = Session(
            id=session_id,
            created_at=now,
            updated_at=now,
            messages=[{"role": "user", "content": "hello"}],
            context={"key": "value"},
            metadata={"tag": "test"},
        )
        d = session.to_dict()
        assert d["id"] == str(session_id)
        assert d["created_at"] == "2026-01-01T12:00:00"
        assert d["updated_at"] == "2026-01-01T12:00:00"
        assert d["messages"] == [{"role": "user", "content": "hello"}]
        assert d["context"] == {"key": "value"}
        assert d["metadata"] == {"tag": "test"}

    def test_from_dict(self) -> None:
        """Session.from_dict should deserialize all fields."""
        data = {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "created_at": "2026-01-01T12:00:00",
            "updated_at": "2026-01-01T12:00:00",
            "messages": [{"role": "user", "content": "hello"}],
            "context": {"key": "value"},
            "metadata": {"tag": "test"},
        }
        session = Session.from_dict(data)
        assert str(session.id) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert session.created_at == datetime(2026, 1, 1, 12, 0, 0)
        assert session.updated_at == datetime(2026, 1, 1, 12, 0, 0)
        assert session.messages == [{"role": "user", "content": "hello"}]
        assert session.context == {"key": "value"}
        assert session.metadata == {"tag": "test"}

    def test_from_dict_partial(self) -> None:
        """Session.from_dict should handle missing fields with defaults."""
        session = Session.from_dict({})
        assert isinstance(session.id, UUID)
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
        assert session.messages == []
        assert session.context == {}
        assert session.metadata == {}

    def test_update_timestamp(self) -> None:
        """update_timestamp should update the updated_at field."""
        session = Session()
        original = session.updated_at
        session.update_timestamp()
        assert session.updated_at >= original


# =============================================================================
# AppState Tests
# =============================================================================


class TestAppState:
    def test_default_creation(self) -> None:
        """AppState should be created with default values."""
        state = AppState()
        assert isinstance(state.session, Session)
        assert state.user == {}
        assert state.config == {}
        assert state.permissions == {}

    def test_creation_with_values(self) -> None:
        """AppState should accept custom values."""
        session = Session()
        state = AppState(
            session=session,
            user={"name": "testuser"},
            config={"theme": "dark"},
            permissions={"read": True},
        )
        assert state.session is session
        assert state.user == {"name": "testuser"}
        assert state.config == {"theme": "dark"}
        assert state.permissions == {"read": True}

    def test_to_dict(self) -> None:
        """AppState.to_dict should serialize all fields."""
        session = Session(
            id=uuid4(),
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        state = AppState(
            session=session,
            user={"name": "testuser"},
            config={"theme": "dark"},
            permissions={"read": True},
        )
        d = state.to_dict()
        assert "session" in d
        assert d["session"]["id"] == str(session.id)
        assert d["user"] == {"name": "testuser"}
        assert d["config"] == {"theme": "dark"}
        assert d["permissions"] == {"read": True}

    def test_from_dict(self) -> None:
        """AppState.from_dict should deserialize all fields."""
        data = {
            "session": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "created_at": "2026-01-01T12:00:00",
                "updated_at": "2026-01-01T12:00:00",
                "messages": [],
                "context": {},
                "metadata": {},
            },
            "user": {"name": "testuser"},
            "config": {"theme": "dark"},
            "permissions": {"read": True},
        }
        state = AppState.from_dict(data)
        assert str(state.session.id) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert state.user == {"name": "testuser"}
        assert state.config == {"theme": "dark"}
        assert state.permissions == {"read": True}

    def test_from_dict_empty(self) -> None:
        """AppState.from_dict should handle empty dict with defaults."""
        state = AppState.from_dict({})
        assert isinstance(state.session, Session)
        assert state.user == {}
        assert state.config == {}
        assert state.permissions == {}

    def test_roundtrip(self) -> None:
        """Serialization roundtrip should preserve all data."""
        original = AppState(
            session=Session(
                messages=[{"role": "user", "content": "hello"}],
                context={"key": "value"},
                metadata={"tag": "test"},
            ),
            user={"name": "testuser"},
            config={"theme": "dark"},
            permissions={"read": True},
        )
        d = original.to_dict()
        restored = AppState.from_dict(d)
        assert str(restored.session.id) == str(original.session.id)
        assert restored.session.messages == original.session.messages
        assert restored.session.context == original.session.context
        assert restored.session.metadata == original.session.metadata
        assert restored.user == original.user
        assert restored.config == original.config
        assert restored.permissions == original.permissions


# =============================================================================
# Helper Tests
# =============================================================================


class TestParseDatetime:
    def test_none_returns_now(self) -> None:
        """_parse_datetime with None should return current time."""
        result = _parse_datetime(None)
        assert isinstance(result, datetime)

    def test_datetime_passthrough(self) -> None:
        """_parse_datetime with datetime should return it unchanged."""
        dt = datetime(2026, 1, 1, 12, 0, 0)
        assert _parse_datetime(dt) == dt

    def test_iso_string_parsing(self) -> None:
        """_parse_datetime should parse ISO format strings."""
        result = _parse_datetime("2026-01-01T12:00:00")
        assert result == datetime(2026, 1, 1, 12, 0, 0)
