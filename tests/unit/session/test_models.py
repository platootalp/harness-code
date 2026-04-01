"""Unit tests for session models."""

from __future__ import annotations

import pytest

from mozi.session.models import (
    Message,
    MessageRole,
    Session,
    SessionStatus,
    SessionSummary,
)


class TestSessionStatus:
    """Unit tests for SessionStatus enum."""

    def test_session_status_values(self) -> None:
        """Test all status values exist."""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.IDLE.value == "idle"
        assert SessionStatus.ARCHIVED.value == "archived"
        assert SessionStatus.EXPIRED.value == "expired"


class TestMessageRole:
    """Unit tests for MessageRole enum."""

    def test_message_role_values(self) -> None:
        """Test all role values exist."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.TOOL.value == "tool"


class TestSessionSummary:
    """Unit tests for SessionSummary."""

    def test_create_summary(self) -> None:
        """Test creating a summary."""
        summary = SessionSummary(
            session_id="test-session",
            content="This is a test summary",
            key_points=["point1", "point2"],
        )

        assert summary.session_id == "test-session"
        assert summary.content == "This is a test summary"
        assert summary.key_points == ["point1", "point2"]
        assert summary.created_at is not None
        assert summary.metadata == {}

    def test_summary_to_dict(self) -> None:
        """Test converting summary to dict."""
        summary = SessionSummary(
            session_id="test-session",
            content="Summary content",
            key_points=["point1"],
        )

        data = summary.to_dict()

        assert data["session_id"] == "test-session"
        assert data["content"] == "Summary content"
        assert data["key_points"] == ["point1"]

    def test_summary_from_dict(self) -> None:
        """Test creating summary from dict."""
        data = {
            "session_id": "test-session",
            "content": "Summary content",
            "key_points": ["point1", "point2"],
            "created_at": "2024-01-01T00:00:00",
            "metadata": {"key": "value"},
        }

        summary = SessionSummary.from_dict(data)

        assert summary.session_id == "test-session"
        assert summary.content == "Summary content"
        assert summary.key_points == ["point1", "point2"]


class TestMessage:
    """Unit tests for Message model."""

    def test_create_message(self) -> None:
        """Test creating a message."""
        message = Message(
            id="msg-1",
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello, world!",
        )

        assert message.id == "msg-1"
        assert message.session_id == "test-session"
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.created_at is not None
        assert message.updated_at is not None
        assert message.metadata == {}
        assert message.streaming_content is None

    def test_message_with_metadata(self) -> None:
        """Test message with metadata."""
        message = Message(
            id="msg-1",
            session_id="test-session",
            role=MessageRole.ASSISTANT,
            content="Hi there!",
            metadata={"model": "claude-3"},
        )

        assert message.metadata["model"] == "claude-3"

    def test_message_to_dict(self) -> None:
        """Test converting message to dict."""
        message = Message(
            id="msg-1",
            session_id="test-session",
            role=MessageRole.USER,
            content="Hello!",
            metadata={"key": "value"},
        )

        data = message.to_dict()

        assert data["id"] == "msg-1"
        assert data["session_id"] == "test-session"
        assert data["role"] == "user"
        assert data["content"] == "Hello!"
        assert data["metadata"] == {"key": "value"}
        assert data["streaming_content"] is None

    def test_message_from_dict(self) -> None:
        """Test creating message from dict."""
        data = {
            "id": "msg-1",
            "session_id": "test-session",
            "role": "assistant",
            "content": "Hello!",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "metadata": {},
            "streaming_content": "Stream",
        }

        message = Message.from_dict(data)

        assert message.id == "msg-1"
        assert message.role == MessageRole.ASSISTANT
        assert message.streaming_content == "Stream"


class TestSession:
    """Unit tests for Session model."""

    def test_create_session(self) -> None:
        """Test creating a session."""
        session = Session(id="test-session")

        assert session.id == "test-session"
        assert session.name is None
        assert session.status == SessionStatus.ACTIVE
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.metadata == {}
        assert session.tags == []

    def test_session_with_all_fields(self) -> None:
        """Test creating a session with all fields."""
        session = Session(
            id="test-session",
            name="My Session",
            user_id="user-123",
            status=SessionStatus.ACTIVE,
            working_dir="/path/to/work",
            model="claude-3",
            system_prompt="You are helpful.",
            tags=["important", "project-a"],
        )

        assert session.name == "My Session"
        assert session.user_id == "user-123"
        assert session.working_dir == "/path/to/work"
        assert session.model == "claude-3"
        assert session.system_prompt == "You are helpful."
        assert session.tags == ["important", "project-a"]

    def test_session_to_dict(self) -> None:
        """Test converting session to dict."""
        session = Session(
            id="test-session",
            name="Test Session",
            status=SessionStatus.ACTIVE,
        )

        data = session.to_dict()

        assert data["id"] == "test-session"
        assert data["name"] == "Test Session"
        assert data["status"] == "active"
        assert data["metadata"] == {}

    def test_session_from_dict(self) -> None:
        """Test creating session from dict."""
        data = {
            "id": "test-session",
            "name": "Test Session",
            "user_id": "user-123",
            "status": "idle",
            "working_dir": "/path",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "last_interaction_at": "2024-01-01T00:00:00",
            "metadata": {"key": "value"},
            "tags": ["tag1"],
            "model": "claude-3",
            "system_prompt": "Be helpful.",
            "summary": None,
        }

        session = Session.from_dict(data)

        assert session.id == "test-session"
        assert session.status == SessionStatus.IDLE
        assert session.tags == ["tag1"]

    def test_session_transition_active_to_idle(self) -> None:
        """Test transitioning from ACTIVE to IDLE."""
        session = Session(id="test-session", status=SessionStatus.ACTIVE)
        session.transition_to(SessionStatus.IDLE)

        assert session.status == SessionStatus.IDLE

    def test_session_transition_idle_to_active(self) -> None:
        """Test transitioning from IDLE to ACTIVE."""
        session = Session(id="test-session", status=SessionStatus.IDLE)
        session.transition_to(SessionStatus.ACTIVE)

        assert session.status == SessionStatus.ACTIVE

    def test_session_transition_idle_to_archived(self) -> None:
        """Test transitioning from IDLE to ARCHIVED."""
        session = Session(id="test-session", status=SessionStatus.IDLE)
        session.transition_to(SessionStatus.ARCHIVED)

        assert session.status == SessionStatus.ARCHIVED

    def test_session_transition_archived_to_expired(self) -> None:
        """Test transitioning from ARCHIVED to EXPIRED."""
        session = Session(id="test-session", status=SessionStatus.ARCHIVED)
        session.transition_to(SessionStatus.EXPIRED)

        assert session.status == SessionStatus.EXPIRED

    def test_invalid_transition(self) -> None:
        """Test that invalid transitions raise ValueError."""
        session = Session(id="test-session", status=SessionStatus.ACTIVE)

        with pytest.raises(ValueError, match="Invalid transition"):
            session.transition_to(SessionStatus.EXPIRED)

    def test_cannot_transition_from_expired(self) -> None:
        """Test that expired sessions cannot transition."""
        session = Session(id="test-session", status=SessionStatus.EXPIRED)

        with pytest.raises(ValueError):
            session.transition_to(SessionStatus.ACTIVE)
