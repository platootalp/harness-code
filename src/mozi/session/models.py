"""Session data models for Mozi.

Defines the core data structures for session management:
- Session: A coding session with state machine
- Message: A message within a session
- SessionStatus: Session lifecycle states
- MessageRole: Roles for messages in a session
- SessionSummary: AI-generated session summary
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SessionStatus(Enum):
    """Session lifecycle states.

    State transitions:
    - ACTIVE → IDLE (when idle timeout reached)
    - IDLE → ACTIVE (when user interacts)
    - IDLE → ARCHIVED (manually or via TTL)
    - ARCHIVED → EXPIRED (after archive TTL)
    """

    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class MessageRole(Enum):
    """Roles for messages in a session."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class SessionSummary:
    """AI-generated summary of a session."""

    session_id: str
    content: str
    key_points: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "session_id": self.session_id,
            "content": self.content,
            "key_points": self.key_points,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionSummary:
        """Create summary from dictionary."""
        created_at_str = data.get("created_at")
        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str)
        else:
            created_at = datetime.utcnow()

        return cls(
            session_id=data["session_id"],
            content=data["content"],
            key_points=data.get("key_points", []),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class Message:
    """A message within a session.

    Supports both regular content and streaming content for AI responses.
    Large content is stored separately as artifacts.
    """

    id: str
    session_id: str
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    streaming_content: str | None = None  # Partial content during streaming

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "streaming_content": self.streaming_content,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Create message from dictionary."""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
            streaming_content=data.get("streaming_content"),
        )


@dataclass
class Session:
    """A coding session with state machine.

    Tracks user interactions with the AI coding agent.
    Supports streaming responses and artifact storage.
    """

    id: str
    name: str | None = None
    user_id: str | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    working_dir: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_interaction_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    model: str | None = None
    system_prompt: str | None = None
    summary: SessionSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "status": self.status.value,
            "working_dir": self.working_dir,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_interaction_at": self.last_interaction_at.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "summary": self.summary.to_dict() if self.summary else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Create session from dictionary."""
        summary_data = data.get("summary")
        summary = SessionSummary.from_dict(summary_data) if summary_data else None

        return cls(
            id=data["id"],
            name=data.get("name"),
            user_id=data.get("user_id"),
            status=SessionStatus(data.get("status", "active")),
            working_dir=data.get("working_dir"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_interaction_at=datetime.fromisoformat(data["last_interaction_at"]),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            model=data.get("model"),
            system_prompt=data.get("system_prompt"),
            summary=summary,
        )

    def transition_to(self, new_status: SessionStatus) -> None:
        """Transition session to a new status.

        Args:
            new_status: The target status to transition to.

        Raises:
            ValueError: If the transition is not allowed.
        """
        allowed_transitions: dict[SessionStatus, list[SessionStatus]] = {
            SessionStatus.ACTIVE: [SessionStatus.IDLE],
            SessionStatus.IDLE: [SessionStatus.ACTIVE, SessionStatus.ARCHIVED],
            SessionStatus.ARCHIVED: [SessionStatus.EXPIRED, SessionStatus.ACTIVE],
            SessionStatus.EXPIRED: [],
        }

        if new_status not in allowed_transitions.get(self.status, []):
            raise ValueError(
                f"Invalid transition from {self.status.value} to {new_status.value}"
            )

        self.status = new_status
        self.updated_at = datetime.utcnow()
