"""Session storage implementation.

TypeScript equivalent: src/services/storage.ts
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StoredSession:
    """Stored session data."""

    session_id: str
    environment_id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredSession:
        """Create from a dictionary."""
        return cls(
            session_id=data["session_id"],
            environment_id=data["environment_id"],
            title=data.get("title"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata"),
        )


class SessionStorage:
    """File-based session storage.

    Stores session data as JSON files in a configured directory.
    Thread-safe for concurrent access within a single process.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        """Initialize session storage.

        Args:
            storage_dir: Directory to store session files.
                        Defaults to ~/.claude/sessions.
        """
        self._storage_dir = storage_dir or (Path.home() / ".claude" / "sessions")
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        """Get path for session file.

        Args:
            session_id: The session identifier.

        Returns:
            Path to the session JSON file.
        """
        return self._storage_dir / f"{session_id}.json"

    async def save(self, session: StoredSession) -> None:
        """Save session to storage.

        Args:
            session: The session to save.
        """
        # Update timestamps
        now = datetime.now(UTC).isoformat()
        if session.created_at is None:
            session.created_at = now
        session.updated_at = now

        path = self._session_path(session.session_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error("Failed to save session %s: %s", session.session_id, e)
            raise

    async def load(self, session_id: str) -> StoredSession | None:
        """Load session from storage.

        Args:
            session_id: The session identifier.

        Returns:
            The stored session, or None if not found.
        """
        path = self._session_path(session_id)
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return StoredSession.from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to load session %s: %s", session_id, e)
            return None

    async def delete(self, session_id: str) -> None:
        """Delete session from storage.

        Args:
            session_id: The session identifier.
        """
        path = self._session_path(session_id)
        try:
            if path.exists():
                path.unlink()
        except OSError as e:
            logger.error("Failed to delete session %s: %s", session_id, e)
            raise

    async def list(self) -> list[StoredSession]:
        """List all sessions.

        Returns:
            List of stored sessions, sorted by updated_at descending.
        """
        sessions: list[StoredSession] = []

        try:
            for path in self._storage_dir.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append(StoredSession.from_dict(data))
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Skipping invalid session file %s: %s", path, e)
        except OSError as e:
            logger.error("Failed to list sessions: %s", e)

        # Sort by updated_at descending
        sessions.sort(
            key=lambda s: s.updated_at or "",
            reverse=True,
        )
        return sessions

    async def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: The session identifier.

        Returns:
            True if the session exists.
        """
        return self._session_path(session_id).exists()
