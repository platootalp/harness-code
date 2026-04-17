"""Session Manager - session lifecycle management."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Session, TokenUsage


class SessionManager:
    """Manages session lifecycle: create, get, update, list, archive."""

    def __init__(self, storage_path: Path | None = None):
        """
        Initialize SessionManager.

        Args:
            storage_path: Optional path for persisting sessions to disk.
                         If None, sessions are only stored in memory.
        """
        self._sessions: dict[str, Session] = {}
        self._storage_path = storage_path
        if storage_path:
            storage_path.mkdir(parents=True, exist_ok=True)

    async def create(self, metadata: dict[str, Any] | None = None) -> Session:
        """
        Create a new session.

        Args:
            metadata: Optional session metadata (user_id, project_path, etc.)

        Returns:
            The newly created Session.
        """
        now = datetime.now()
        session = Session(
            id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
            status="active",
            token_usage=TokenUsage(),
        )
        self._sessions[session.id] = session
        if self._storage_path:
            await self._persist(session)
        return session

    async def get(self, session_id: str) -> Session | None:
        """
        Retrieve a session by ID.

        Args:
            session_id: The session ID.

        Returns:
            The Session if found, None otherwise.
        """
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Try loading from disk if not in memory
        if self._storage_path:
            session = await self._load(session_id)
            if session:
                self._sessions[session_id] = session
            return session
        return None

    async def update(self, session_id: str, updates: dict[str, Any]) -> Session:
        """
        Update a session's fields.

        Args:
            session_id: The session ID.
            updates: Dictionary of fields to update.

        Returns:
            The updated Session.

        Raises:
            KeyError: If the session does not exist.
        """
        session = await self.get(session_id)
        if not session:
            raise KeyError(f"Session not found: {session_id}")

        # Apply updates
        if "status" in updates:
            session.status = updates["status"]
        if "metadata" in updates:
            session.metadata.update(updates["metadata"])
        if "task_ids" in updates:
            session.task_ids = updates["task_ids"]
        if "agent_ids" in updates:
            session.agent_ids = updates["agent_ids"]
        if "token_usage" in updates:
            tu = updates["token_usage"]
            if isinstance(tu, dict):
                session.token_usage = TokenUsage.from_dict(tu)
            else:
                session.token_usage = tu
        if "tool_calls" in updates:
            session.tool_calls = updates["tool_calls"]
        if "errors" in updates:
            session.errors = updates["errors"]

        session.updated_at = datetime.now()

        if self._storage_path:
            await self._persist(session)
        return session

    async def list(self, status: str | None = None) -> list[Session]:
        """
        List sessions, optionally filtered by status.

        Args:
            status: If provided, only return sessions with this status.
                   One of: active, paused, completed, archived.

        Returns:
            List of matching sessions, newest first.
        """
        sessions = list(self._sessions.values())
        if status is not None:
            sessions = [s for s in sessions if s.status == status]
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    async def archive(self, session_id: str) -> None:
        """
        Archive a session (marks as archived).

        Args:
            session_id: The session ID to archive.

        Raises:
            KeyError: If the session does not exist.
        """
        session = await self.get(session_id)
        if not session:
            raise KeyError(f"Session not found: {session_id}")
        await self.update(session_id, {"status": "archived"})

    async def increment_tool_calls(self, session_id: str) -> None:
        """Increment the tool call counter for a session."""
        session = await self.get(session_id)
        if session:
            session.tool_calls += 1
            session.updated_at = datetime.now()

    async def increment_errors(self, session_id: str) -> None:
        """Increment the error counter for a session."""
        session = await self.get(session_id)
        if session:
            session.errors += 1
            session.updated_at = datetime.now()

    async def add_token_usage(
        self,
        session_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Add token usage to a session."""
        session = await self.get(session_id)
        if session:
            session.token_usage.add(prompt_tokens, completion_tokens, cost_usd)
            session.updated_at = datetime.now()

    # --- Persistence helpers ---

    async def _persist(self, session: Session) -> None:
        """Write session to disk."""
        import json
        if not self._storage_path:
            return
        path = self._storage_path / f"{session.id}.json"
        path.write_text(json.dumps(session.to_dict(), indent=2))

    async def _load(self, session_id: str) -> Session | None:
        """Load session from disk."""
        import json
        if not self._storage_path:
            return None
        path = self._storage_path / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return Session.from_dict(data)
