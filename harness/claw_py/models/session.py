"""
Session and AppState data models.

Provides core data structures for session management:
- Session: Represents a conversation session with messages and metadata
- AppState: Global application state containing session, user, config, and permissions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

# =============================================================================
# Session
# =============================================================================


@dataclass
class Session:
    """Represents a conversation session.

    Attributes:
        id: Unique session identifier.
        created_at: When the session was created.
        updated_at: When the session was last updated.
        messages: List of messages in the session.
        context: Arbitrary session context data.
        metadata: Additional session metadata.
    """

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    messages: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the session to a dictionary.

        Returns:
            Dictionary representation of the session.
        """
        return {
            "id": str(self.id),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": self.messages,
            "context": self.context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        """Deserialize a session from a dictionary.

        Args:
            data: Dictionary containing session data.

        Returns:
            A Session instance.
        """
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            messages=data.get("messages", []),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
        )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.utcnow()


# =============================================================================
# AppState
# =============================================================================


@dataclass
class AppState:
    """Global application state.

    Attributes:
        session: The current session.
        user: User information and preferences.
        config: Application configuration.
        permissions: Permission settings and context.
    """

    session: Session = field(default_factory=Session)
    user: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    permissions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the app state to a dictionary.

        Returns:
            Dictionary representation of the app state.
        """
        return {
            "session": self.session.to_dict(),
            "user": self.user,
            "config": self.config,
            "permissions": self.permissions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppState:
        """Deserialize app state from a dictionary.

        Args:
            data: Dictionary containing app state data.

        Returns:
            An AppState instance.
        """
        session_data = data.get("session", {})
        session = Session.from_dict(session_data) if session_data else Session()
        return cls(
            session=session,
            user=data.get("user", {}),
            config=data.get("config", {}),
            permissions=data.get("permissions", {}),
        )


# =============================================================================
# Helpers
# =============================================================================


def _parse_datetime(value: str | datetime | None) -> datetime:
    """Parse a datetime value from ISO string or datetime.

    Args:
        value: ISO format string or datetime object.

    Returns:
        A datetime instance.
    """
    if value is None:
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
