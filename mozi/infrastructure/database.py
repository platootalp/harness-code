"""SQLite-based session storage implementation.

This module provides an async SQLite storage implementation for session
and message persistence using aiosqlite. Large results (>10KB) are stored
as files in the artifacts directory.

Database Schema:
    - sessions: Session metadata
    - messages: Message records linked to sessions
    - artifacts: Large content stored as files

Exceptions:
    - DatabaseError: Raised for storage operation failures
    - SessionNotFoundError: Raised when session does not exist
    - SessionCorruptedError: Raised for data corruption issues
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite

from mozi.exceptions import (
    DatabaseError,
    SessionCorruptedError,
)


class SessionStatus(Enum):
    """Session status enumeration.

    Attributes:
        ACTIVE: Session is actively in use.
        IDLE: Session has been inactive for a period.
        ARCHIVED: Session has been archived.
        EXPIRED: Session has expired and can be cleaned up.
    """

    ACTIVE = "active"
    IDLE = "idle"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class MessageRole(Enum):
    """Message role enumeration.

    Attributes:
        SYSTEM: System-generated message.
        USER: User-provided message.
        ASSISTANT: Assistant-generated response.
        TOOL: Result from a tool execution.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Session:
    """Session data model.

    Attributes:
        id: Unique session identifier (UUID).
        name: Optional session name.
        working_dir: Working directory for the session.
        status: Current session status.
        metadata: Additional session metadata.
        user_id: Optional user identifier.
        tags: List of session tags.
        created_at: Session creation timestamp.
        updated_at: Last update timestamp.
        last_active_at: Last activity timestamp.
    """

    id: str
    name: str = ""
    working_dir: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_active_at: datetime = field(default_factory=datetime.now)


@dataclass
class Message:
    """Message data model.

    Attributes:
        id: Unique message identifier (UUID).
        session_id: Parent session identifier.
        role: Message role (system, user, assistant, tool).
        content: Message content.
        created_at: Message creation timestamp.
        metadata: Additional message metadata.
    """

    id: str
    session_id: str
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class SQLiteSessionStorage:
    """SQLite-based session storage implementation.

    This class provides async persistence for sessions and messages using
    SQLite with WAL mode for concurrent access. Large content (>10KB) is
    stored as files in the artifacts directory.

    Attributes:
        db_path: Path to the SQLite database file.
        artifacts_dir: Directory for storing large content files.
        artifact_threshold: Size threshold in bytes for artifact storage.

    Example:
        ```python
        storage = SQLiteSessionStorage()
        session = Session(id="test-123", name="Test Session")
        await storage.save_session(session)
        loaded = await storage.load_session("test-123")
        ```
    """

    DEFAULT_DB_PATH: str = "~/.mozi/sessions.db"
    DEFAULT_ARTIFACTS_DIR: str = "~/.mozi/storage/artifacts"
    ARTIFACT_THRESHOLD: int = 10 * 1024  # 10KB

    def __init__(
        self,
        db_path: str | None = None,
        artifacts_dir: str | None = None,
        artifact_threshold: int | None = None,
    ) -> None:
        """Initialize SQLite session storage.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.mozi/sessions.db.
            artifacts_dir: Directory for large content files.
                Defaults to ~/.mozi/storage/artifacts.
            artifact_threshold: Size threshold for artifact storage in bytes.
                Defaults to 10KB.
        """
        self._db_path = Path(db_path or self.DEFAULT_DB_PATH).expanduser()
        self._artifacts_dir = Path(
            artifacts_dir or self.DEFAULT_ARTIFACTS_DIR
        ).expanduser()
        self._artifact_threshold = (
            artifact_threshold or self.ARTIFACT_THRESHOLD
        )
        self._db: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """Initialize database tables and directories.

        Creates the database file, artifacts directory, and all required
        tables (sessions, messages, artifacts) with proper indexes.

        Raises:
            DatabaseError: If database initialization fails.
        """
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._artifacts_dir.mkdir(parents=True, exist_ok=True)

            self._db = await aiosqlite.connect(str(self._db_path))
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("PRAGMA busy_timeout=5000")
            await self._db.execute("PRAGMA foreign_keys=ON")

            await self._db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    working_dir TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    metadata TEXT NOT NULL DEFAULT '{}',
                    user_id TEXT,
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    artifact_path TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                    ON messages(session_id);

                CREATE INDEX IF NOT EXISTS idx_artifacts_message_id
                    ON artifacts(message_id);
            """)
            await self._db.commit()

        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    async def _ensure_db(self) -> aiosqlite.Connection:
        """Ensure database connection is established.

        Returns:
            Active database connection.

        Raises:
            DatabaseError: If database is not initialized.
        """
        if self._db is None:
            await self.init_db()
        if self._db is None:
            raise DatabaseError("Database connection not available")
        return self._db

    def _serialize_session(self, session: Session) -> dict[str, str]:
        """Serialize session to database row format.

        Args:
            session: Session object to serialize.

        Returns:
            Dictionary with string values suitable for database insertion.
        """
        return {
            "id": session.id,
            "name": session.name,
            "working_dir": session.working_dir,
            "status": session.status.value,
            "metadata": json.dumps(session.metadata),
            "user_id": session.user_id or "",
            "tags": json.dumps(session.tags),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "last_active_at": session.last_active_at.isoformat(),
        }

    def _deserialize_session(self, row: tuple[Any, ...]) -> Session:
        """Deserialize database row to Session object.

        Args:
            row: Database row tuple.

        Returns:
            Deserialized Session object.

        Raises:
            SessionCorruptedError: If session data cannot be parsed.
        """
        try:
            (
                id,
                name,
                working_dir,
                status,
                metadata,
                user_id,
                tags,
                created_at,
                updated_at,
                last_active_at,
            ) = row

            return Session(
                id=id,
                name=name,
                working_dir=working_dir,
                status=SessionStatus(status),
                metadata=json.loads(metadata) if metadata else {},
                user_id=user_id if user_id else None,
                tags=json.loads(tags) if tags else [],
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at),
                last_active_at=datetime.fromisoformat(last_active_at),
            )
        except (json.JSONDecodeError, ValueError) as e:
            raise SessionCorruptedError(
                f"Failed to deserialize session: {e}"
            ) from e

    def _serialize_message(self, message: Message) -> tuple[str, str, str, str, str, str, str]:
        """Serialize message to database row format.

        Args:
            message: Message object to serialize.

        Returns:
            Tuple of (id, session_id, role, content, created_at, metadata, artifact_path).
        """
        artifact_path = ""
        content = message.content

        if len(content.encode("utf-8")) > self._artifact_threshold:
            artifact_path = self._save_artifact(message.id, content)
            content = ""

        return (
            message.id,
            message.session_id,
            message.role.value,
            content,
            message.created_at.isoformat(),
            json.dumps(message.metadata),
            artifact_path,
        )

    def _save_artifact(self, message_id: str, content: str) -> str:
        """Save large content to artifact file.

        Uses atomic write (write-then-rename) to ensure consistency.

        Args:
            message_id: Associated message identifier.
            content: Content to save.

        Returns:
            Path to the saved artifact file.

        Raises:
            DatabaseError: If artifact write fails.
        """
        artifact_filename = f"{message_id}.artifact"
        artifact_path = self._artifacts_dir / artifact_filename

        temp_fd, temp_path = tempfile.mkstemp(
            dir=str(self._artifacts_dir),
            prefix=".tmp_",
            suffix=".artifact",
        )

        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.rename(temp_path, str(artifact_path))
        except OSError as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise DatabaseError(f"Failed to save artifact: {e}") from e

        return str(artifact_path)

    def _load_artifact(self, artifact_path: str) -> str:
        """Load content from artifact file.

        Args:
            artifact_path: Path to the artifact file.

        Returns:
            Content of the artifact file.

        Raises:
            DatabaseError: If artifact read fails.
        """
        try:
            with open(artifact_path) as f:
                return f.read()
        except OSError as e:
            raise DatabaseError(f"Failed to load artifact: {e}") from e

    def _deserialize_message(
        self, row: tuple[Any, ...], load_content: bool = True
    ) -> Message:
        """Deserialize database row to Message object.

        Args:
            row: Database row tuple.
            load_content: Whether to load artifact content if present.

        Returns:
            Deserialized Message object.
        """
        (
            id,
            session_id,
            role,
            content,
            created_at,
            metadata,
            artifact_path,
        ) = row

        if artifact_path and load_content:
            content = self._load_artifact(artifact_path)

        return Message(
            id=id,
            session_id=session_id,
            role=MessageRole(role),
            content=content,
            created_at=datetime.fromisoformat(created_at),
            metadata=json.loads(metadata) if metadata else {},
        )

    async def save_session(self, session: Session) -> None:
        """Save or update a session.

        Args:
            session: Session object to save.

        Raises:
            DatabaseError: If save operation fails.
        """
        db = await self._ensure_db()
        data = self._serialize_session(session)

        try:
            await db.execute(
                """
                INSERT INTO sessions (
                    id, name, working_dir, status, metadata,
                    user_id, tags, created_at, updated_at, last_active_at
                ) VALUES (
                    :id, :name, :working_dir, :status, :metadata,
                    :user_id, :tags, :created_at, :updated_at, :last_active_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name = :name,
                    working_dir = :working_dir,
                    status = :status,
                    metadata = :metadata,
                    user_id = :user_id,
                    tags = :tags,
                    updated_at = :updated_at,
                    last_active_at = :last_active_at
                """,
                data,
            )
            await db.commit()
        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to save session: {e}") from e

    async def load_session(self, session_id: str) -> Session | None:
        """Load a session by ID.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session object if found, None otherwise.

        Raises:
            DatabaseError: If load operation fails.
            SessionCorruptedError: If session data is corrupted.
        """
        db = await self._ensure_db()

        try:
            async with db.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                return None

            return self._deserialize_session(row)  # type: ignore[arg-type]

        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to load session: {e}") from e

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its associated messages.

        Args:
            session_id: Unique session identifier.

        Returns:
            True if session was deleted, False if not found.

        Raises:
            DatabaseError: If delete operation fails.
        """
        db = await self._ensure_db()

        try:
            async with db.execute(
                "SELECT id FROM sessions WHERE id = ?",
                (session_id,),
            ) as cursor:
                if await cursor.fetchone() is None:
                    return False

            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return True

        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to delete session: {e}") from e

    async def list_sessions(
        self,
        status: SessionStatus | None = None,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[Session]:
        """List sessions with optional filtering.

        Args:
            status: Filter by session status.
            user_id: Filter by user identifier.
            limit: Maximum number of sessions to return.

        Returns:
            List of matching Session objects.

        Raises:
            DatabaseError: If list operation fails.
            SessionCorruptedError: If any session data is corrupted.
        """
        db = await self._ensure_db()

        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)

        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)

        query += " ORDER BY last_active_at DESC LIMIT ?"
        params.append(limit)

        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

            return [self._deserialize_session(row) for row in rows]  # type: ignore[arg-type]

        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to list sessions: {e}") from e

    async def save_message(self, message: Message) -> None:
        """Save a message.

        Large content (>10KB) is automatically stored as an artifact file.

        Args:
            message: Message object to save.

        Raises:
            DatabaseError: If save operation fails.
        """
        db = await self._ensure_db()
        data = self._serialize_message(message)

        try:
            await db.execute(
                """
                INSERT INTO messages (
                    id, session_id, role, content,
                    created_at, metadata, artifact_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    metadata = excluded.metadata,
                    artifact_path = excluded.artifact_path
                """,
                data,
            )
            await db.commit()
        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to save message: {e}") from e

    async def load_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[Message]:
        """Load messages for a session.

        Args:
            session_id: Parent session identifier.
            limit: Maximum number of messages to return (newest first).

        Returns:
            List of Message objects ordered by creation time.

        Raises:
            DatabaseError: If load operation fails.
        """
        db = await self._ensure_db()

        query = """
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        """
        params: list[Any] = [session_id]

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        try:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

            return [self._deserialize_message(row) for row in rows]  # type: ignore[arg-type]

        except aiosqlite.Error as e:
            raise DatabaseError(f"Failed to load messages: {e}") from e

    async def close(self) -> None:
        """Close database connection.

        Raises:
            DatabaseError: If close operation fails.
        """
        if self._db is not None:
            try:
                await self._db.close()
            except aiosqlite.Error as e:
                raise DatabaseError(f"Failed to close database: {e}") from e
            finally:
                self._db = None

    async def __aenter__(self) -> SQLiteSessionStorage:
        """Enter async context manager.

        Returns:
            Self for use in async with statement.
        """
        await self.init_db()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager.

        Args:
            exc_type: Exception type if an error occurred.
            exc_val: Exception value if an error occurred.
            exc_tb: Exception traceback if an error occurred.
        """
        await self.close()
