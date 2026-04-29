"""Session management for bridge connections.

Handles session lifecycle: create, reconnect, archive, and crash recovery
via bridge pointer files.

TypeScript equivalent: src/bridge/createSession.ts, src/bridge/bridgeApi.ts
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default bridge pointer file location
_BRIDGE_POINTER_DIR = Path.home() / ".claude" / "bridge"
_BRIDGE_POINTER_FILE = _BRIDGE_POINTER_DIR / "bridge_pointer.json"


# =============================================================================
# Session Info
# =============================================================================


@dataclass
class SessionInfo:
    """Information about a bridge session.

    Attributes:
        session_id: Unique identifier for this session.
        environment_id: Backend-issued environment identifier (set after registration).
        title: Optional human-readable session title.
        created_at: ISO 8601 timestamp when session was created.
    """

    session_id: str
    environment_id: str | None = None
    title: str | None = None
    created_at: str | None = None


# =============================================================================
# Bridge Pointer (Crash Recovery)
# =============================================================================


@dataclass
class BridgePointer:
    """Bridge pointer file data for crash recovery.

    Written to disk so that if the bridge process crashes, a new instance
    can reconnect to the existing session.

    Attributes:
        session_id: The session ID to reconnect to.
        environment_id: The environment ID to reconnect to.
        source: Origin of the pointer (e.g. "repl", "remote-control").
    """

    session_id: str
    environment_id: str | None = None
    source: str = "repl"


# =============================================================================
# Session Manager
# =============================================================================


class SessionManager:
    """Manages bridge session lifecycle.

    Handles creating new sessions, reconnecting to existing ones, archiving
    completed sessions, and writing/reading bridge pointer files for crash
    recovery.

    TypeScript equivalent: createSession.ts, bridgeApi.ts

    Attributes:
        base_url: API base URL for session management endpoints.
        http_client: Shared HTTP client for API calls.
        pointer_dir: Directory for bridge pointer files.
    """

    def __init__(
        self,
        base_url: str = "https://api.claude.ai",
        http_client: httpx.AsyncClient | None = None,
        pointer_dir: Path | None = None,
    ) -> None:
        """Initialize session manager.

        Args:
            base_url: API base URL for session management.
            http_client: Optional shared HTTP client. If not provided,
                a new httpx.AsyncClient is created on first use.
            pointer_dir: Directory for bridge pointer files. Defaults
                to ~/.claude/bridge/.
        """
        self.base_url = base_url
        self._http_client = http_client
        self._owned_client = False
        self._pointer_dir = pointer_dir or _BRIDGE_POINTER_DIR

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            )
            self._owned_client = True
        return self._http_client

    async def _close_client(self) -> None:
        """Close the owned HTTP client if we created it."""
        if self._owned_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
            self._owned_client = False

    # -------------------------------------------------------------------------
    # Session Lifecycle
    # -------------------------------------------------------------------------

    async def create_session(
        self,
        title: str | None = None,
        git_context: dict[str, Any] | None = None,
    ) -> SessionInfo:
        """Create a new bridge session.

        Args:
            title: Optional human-readable title for the session.
            git_context: Optional git context to include (repo, branch, etc.).

        Returns:
            SessionInfo with the new session's ID and metadata.

        Raises:
            httpx.HTTPError: If the API call fails.
        """
        session_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()

        client = await self._get_client()

        payload: dict[str, Any] = {
            "session_id": session_id,
        }
        if title:
            payload["title"] = title
        if git_context:
            payload["git_context"] = git_context

        try:
            response = await client.post("/v1/sessions", json=payload)
            response.raise_for_status()
            data = response.json()

            return SessionInfo(
                session_id=session_id,
                environment_id=data.get("environment_id"),
                title=data.get("title", title),
                created_at=data.get("created_at", created_at),
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to create session via API: {e}")
            # Return local info if API is unavailable
            return SessionInfo(
                session_id=session_id,
                title=title,
                created_at=created_at,
            )

    async def reconnect_session(
        self,
        session_id: str,
        environment_id: str | None = None,
    ) -> SessionInfo:
        """Reconnect to an existing session.

        Used when resuming a session after the original bridge process died.

        Args:
            session_id: The session ID to reconnect to.
            environment_id: Optional environment ID for the session.

        Returns:
            SessionInfo with reconnected session metadata.

        Raises:
            httpx.HTTPError: If the API call fails.
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"/v1/sessions/{session_id}/reconnect",
                json={"environment_id": environment_id} if environment_id else {},
            )
            response.raise_for_status()
            data = response.json()

            return SessionInfo(
                session_id=session_id,
                environment_id=data.get("environment_id", environment_id),
                title=data.get("title"),
                created_at=data.get("created_at"),
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to reconnect session via API: {e}")
            # Return local info if API is unavailable
            return SessionInfo(
                session_id=session_id,
                environment_id=environment_id,
            )

    async def archive_session(self, session_id: str) -> None:
        """Archive (end) a session.

        Archived sessions no longer appear as active on the server.

        Args:
            session_id: The session ID to archive.

        Raises:
            httpx.HTTPError: If the API call fails.
        """
        client = await self._get_client()

        try:
            response = await client.post(f"/v1/sessions/{session_id}/archive")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to archive session: {e}")

    async def update_session_title(
        self,
        session_id: str,
        title: str,
    ) -> None:
        """Update a session's title.

        Args:
            session_id: The session ID to update.
            title: The new title.

        Raises:
            httpx.HTTPError: If the API call fails.
        """
        client = await self._get_client()

        try:
            response = await client.put(
                f"/v1/sessions/{session_id}/title",
                json={"title": title},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to update session title: {e}")

    # -------------------------------------------------------------------------
    # Bridge Pointer (Crash Recovery)
    # -------------------------------------------------------------------------

    def write_bridge_pointer(
        self,
        session_id: str,
        environment_id: str | None = None,
        source: str = "repl",
    ) -> Path:
        """Write bridge pointer file for crash recovery.

        Writes a JSON file to ~/.claude/bridge/bridge_pointer.json that
        allows a new bridge instance to reconnect to an existing session.

        Args:
            session_id: The session ID to store.
            environment_id: Optional environment ID to store.
            source: Origin identifier (e.g. "repl", "remote-control").

        Returns:
            Path to the written pointer file.
        """
        self._pointer_dir.mkdir(parents=True, exist_ok=True)

        pointer = BridgePointer(
            session_id=session_id,
            environment_id=environment_id,
            source=source,
        )

        data = {
            "sessionId": pointer.session_id,
            "environmentId": pointer.environment_id,
            "source": pointer.source,
        }

        path = self._pointer_dir / "bridge_pointer.json"
        path.write_text(json.dumps(data, indent=2))
        logger.debug(f"Wrote bridge pointer to {path}")

        return path

    def read_bridge_pointer(self) -> BridgePointer | None:
        """Read bridge pointer file for reconnection.

        Returns the stored session/environment IDs if a bridge pointer file
        exists from a previous session.

        Returns:
            BridgePointer with stored IDs, or None if no pointer file exists.
        """
        path = self._pointer_dir / "bridge_pointer.json"

        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text())
            return BridgePointer(
                session_id=data.get("sessionId", ""),
                environment_id=data.get("environmentId"),
                source=data.get("source", "repl"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read bridge pointer: {e}")
            return None

    def clear_bridge_pointer(self) -> None:
        """Remove the bridge pointer file.

        Called after successful session teardown to prevent stale reconnects.
        """
        path = self._pointer_dir / "bridge_pointer.json"
        if path.exists():
            try:
                path.unlink()
                logger.debug(f"Removed bridge pointer at {path}")
            except OSError as e:
                logger.warning(f"Failed to remove bridge pointer: {e}")

    def get_pointer_path(self) -> Path:
        """Get the expected bridge pointer file path."""
        return self._pointer_dir / "bridge_pointer.json"
