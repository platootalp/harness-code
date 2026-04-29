"""SQLite-based session storage implementation.

Provides persistent storage for sessions and messages using SQLite.
Supports large message content as artifacts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from mozi.session.models import (
    Message,
    MessageRole,
    Session,
    SessionStatus,
    SessionSummary,
)
from mozi.session.storage import SessionStorage

# Large content threshold: 10KB
LARGE_CONTENT_THRESHOLD = 10 * 1024


class SQLiteSessionStorage(SessionStorage):
    """SQLite-based session storage.

    Uses WAL mode for better concurrent access and supports
    storing large content as separate artifacts.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        artifact_dir: str | Path | None = None,
    ) -> None:
        """Initialize SQLite session storage.

        Args:
            db_path: Path to the SQLite database file.
                     Defaults to ~/.mozisessions.db
            artifact_dir: Directory for large content artifacts.
                          Defaults to ~/.src/artifacts/
        """
        if db_path is None:
            home = os.path.expanduser("~")
            db_path = os.path.join(home, ".mozisessions.db")

        self._db_path = str(db_path)
        self._db: aiosqlite.Connection | None = None
        self._init_done = False

        if artifact_dir is None:
            home = os.path.expanduser("~")
            artifact_dir = os.path.join(home, ".src", "artifacts")
        self._artifact_dir = Path(artifact_dir)
        self._artifact_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self) -> SQLiteSessionStorage:
        """Enter async context manager."""
        await self.init()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        await self.close()

    async def init(self) -> None:
        """Initialize the database connection and create tables."""
        if self._init_done:
            return

        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        # Enable WAL mode for better concurrent access
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

        # Create tables
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT,
                user_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                working_dir TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_interaction_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                tags TEXT NOT NULL DEFAULT '[]',
                model TEXT,
                system_prompt TEXT,
                summary TEXT
            )
        """)

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                streaming_content TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)

        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            )
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id)
        """)

        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_status
            ON sessions(status)
        """)

        await self._db.commit()
        self._init_done = True

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
            self._init_done = False

    async def _ensure_db(self) -> aiosqlite.Connection:
        """Ensure database is initialized."""
        if self._db is None:
            raise RuntimeError("Storage not initialized. Call init() first.")
        return self._db

    def _session_from_row(self, row: aiosqlite.Row) -> Session:
        """Convert a database row to a Session object."""
        summary_data = row["summary"]
        summary = None
        if summary_data:
            summary = SessionSummary.from_dict(json.loads(summary_data))

        # Parse datetime strings if needed
        created_at = row["created_at"]
        updated_at = row["updated_at"]
        last_interaction_at = row["last_interaction_at"]

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        if isinstance(last_interaction_at, str):
            last_interaction_at = datetime.fromisoformat(last_interaction_at)

        return Session(
            id=row["id"],
            name=row["name"],
            user_id=row["user_id"],
            status=SessionStatus(row["status"]),
            working_dir=row["working_dir"],
            created_at=created_at,
            updated_at=updated_at,
            last_interaction_at=last_interaction_at,
            metadata=json.loads(row["metadata"]),
            tags=json.loads(row["tags"]),
            model=row["model"],
            system_prompt=row["system_prompt"],
            summary=summary,
        )

    def _message_from_row(self, row: aiosqlite.Row) -> Message:
        """Convert a database row to a Message object."""
        # Parse datetime strings if needed
        created_at = row["created_at"]
        updated_at = row["updated_at"]

        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return Message(
            id=row["id"],
            session_id=row["session_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            created_at=created_at,
            updated_at=updated_at,
            metadata=json.loads(row["metadata"]),
            streaming_content=row["streaming_content"],
        )

    async def save_session(self, session: Session) -> None:
        """Save a session to the database.

        Uses INSERT ... ON CONFLICT DO UPDATE to avoid triggering
        foreign key cascades that would delete associated messages.
        """
        db = await self._ensure_db()

        # Handle summary serialization
        summary_json = json.dumps(session.summary.to_dict()) if session.summary else None

        await db.execute("""
            INSERT INTO sessions
            (id, name, user_id, status, working_dir, created_at, updated_at,
             last_interaction_at, metadata, tags, model, system_prompt, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                user_id = excluded.user_id,
                status = excluded.status,
                working_dir = excluded.working_dir,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                last_interaction_at = excluded.last_interaction_at,
                metadata = excluded.metadata,
                tags = excluded.tags,
                model = excluded.model,
                system_prompt = excluded.system_prompt,
                summary = excluded.summary
        """, (
            session.id,
            session.name,
            session.user_id,
            session.status.value,
            session.working_dir,
            session.created_at,
            session.updated_at,
            session.last_interaction_at,
            json.dumps(session.metadata),
            json.dumps(session.tags),
            session.model,
            session.system_prompt,
            summary_json,
        ))
        await db.commit()

    async def load_session(self, session_id: str) -> Session | None:
        """Load a session by ID."""
        db = await self._ensure_db()

        async with db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._session_from_row(row)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its messages."""
        db = await self._ensure_db()

        cursor = await db.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

    async def list_sessions(
        self,
        status: SessionStatus | None = None,
        limit: int | None = None,
    ) -> list[Session]:
        """List sessions with optional filtering."""
        db = await self._ensure_db()

        query = "SELECT * FROM sessions"
        params: list[Any] = []

        if status is not None:
            query += " WHERE status = ?"
            params.append(status.value)

        query += " ORDER BY updated_at DESC"

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._session_from_row(row) for row in rows]

    async def save_message(self, message: Message) -> None:
        """Save a message to the database.

        Large content (>10KB) is stored as a separate artifact.
        Uses INSERT ... ON CONFLICT DO UPDATE to avoid foreign key cascade issues.
        """
        db = await self._ensure_db()

        content_to_store = message.content
        artifact_id = None

        # First insert the message (even if content will be replaced with artifact ref)
        await db.execute("""
            INSERT INTO messages
            (id, session_id, role, content, created_at, updated_at, metadata, streaming_content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                session_id = excluded.session_id,
                role = excluded.role,
                content = excluded.content,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                metadata = excluded.metadata,
                streaming_content = excluded.streaming_content
        """, (
            message.id,
            message.session_id,
            message.role.value,
            content_to_store,
            message.created_at,
            message.updated_at,
            json.dumps(message.metadata),
            message.streaming_content,
        ))

        # Then store large content as artifact if needed
        if len(message.content) > LARGE_CONTENT_THRESHOLD:
            artifact_id = f"{message.id}-artifact"
            await db.execute("""
                INSERT INTO artifacts (id, message_id, content, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    content = excluded.content,
                    created_at = excluded.created_at
            """, (
                artifact_id,
                message.id,
                message.content,
                message.created_at,
            ))

            # Update the message with artifact reference
            await db.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (f"[artifact:{artifact_id}]", message.id),
            )

        await db.commit()

    async def load_messages(self, session_id: str) -> list[Message]:
        """Load all messages for a session."""
        db = await self._ensure_db()

        async with db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            messages = []
            for row in rows:
                message = self._message_from_row(row)
                # Load content from artifact if needed
                if message.content.startswith("[artifact:"):
                    artifact_id = message.content[10:-1]
                    async with db.execute(
                        "SELECT content FROM artifacts WHERE id = ?",
                        (artifact_id,),
                    ) as art_cursor:
                        art_row = await art_cursor.fetchone()
                        if art_row:
                            message.content = art_row["content"]
                messages.append(message)
            return messages

    async def update_message(
        self,
        message_id: str,
        content: str | None = None,
        streaming_content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a message's content, streaming content, or metadata."""
        db = await self._ensure_db()

        updates: list[str] = []
        params: list[Any] = []

        if content is not None:
            updates.append("content = ?")
            params.append(content)

        if streaming_content is not None:
            updates.append("streaming_content = ?")
            params.append(streaming_content)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return False

        from datetime import datetime
        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(message_id)

        cursor = await db.execute(
            f"UPDATE messages SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()
        return cursor.rowcount > 0
