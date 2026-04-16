"""Session persistence and transcript management utilities."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

MAX_TRANSCRIPT_READ_BYTES = 50 * 1024 * 1024  # 50MB
MAX_TOMBSTONE_REWRITE_BYTES = 50 * 1024 * 1024  # 50MB

_PROJECTS_DIR_NAME = ".claude"
_PROJECTS_DIR_SUBDIR = "projects"
_SESSIONS_DIR_NAME = "sessions"
_TRANSCRIPT_EXT = ".jsonl"


# =============================================================================
# Project Directory
# =============================================================================


def get_projects_dir() -> str:
    """Get the projects directory path.

    Returns:
        Absolute path to the projects directory.
    """
    config_home = os.environ.get(
        "CLAUDE_CONFIG_HOME",
        os.path.join(os.path.expanduser("~"), ".config", "claude"),
    )
    return os.path.join(config_home, _PROJECTS_DIR_NAME, _PROJECTS_DIR_SUBDIR)


def get_transcript_path() -> str:
    """Get the current session transcript path.

    Returns:
        Path to the current session transcript file.
    """
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")
    return get_transcript_path_for_session(session_id)


def get_transcript_path_for_session(session_id: str) -> str:
    """Get the transcript path for a specific session.

    Args:
        session_id: The session ID.

    Returns:
        Path to the session transcript file.
    """
    projects_dir = get_projects_dir()
    return os.path.join(
        projects_dir, _SESSIONS_DIR_NAME, f"{session_id}{_TRANSCRIPT_EXT}"
    )


def get_agent_transcript_path(agent_id: str) -> str:
    """Get the transcript path for a subagent.

    Args:
        agent_id: The agent ID.

    Returns:
        Path to the agent's transcript file.
    """
    projects_dir = get_projects_dir()
    return os.path.join(
        projects_dir, _SESSIONS_DIR_NAME, f"agent_{agent_id}{_TRANSCRIPT_EXT}"
    )


def session_id_exists(session_id: str) -> bool:
    """Check if a session file exists.

    Args:
        session_id: The session ID to check.

    Returns:
        True if the session file exists.
    """
    path = get_transcript_path_for_session(session_id)
    return os.path.exists(path)


# =============================================================================
# Entry Types
# =============================================================================


@dataclass
class Entry:
    """A session transcript entry."""

    ts: str = ""
    type: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        """Serialize entry as a JSONL line.

        Returns:
            JSON string followed by newline.
        """
        return json.dumps({"ts": self.ts, "type": self.type, "data": self.data}, ensure_ascii=False) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entry:
        """Create an Entry from a dictionary.

        Args:
            data: Dict with ts, type, and data fields.

        Returns:
            A new Entry instance.
        """
        return cls(
            ts=data.get("ts", ""),
            type=data.get("type", ""),
            data=data.get("data", {}),
        )


# =============================================================================
# Metadata
# =============================================================================


@dataclass
class AgentMetadata:
    """Metadata for a subagent."""

    agent_type: str
    worktree_path: str | None = None
    description: str | None = None


@dataclass
class RemoteAgentMetadata:
    """Metadata for a remote agent."""

    task_id: str
    remote_task_type: str
    session_id: str
    title: str
    command: str
    spawned_at: int


# =============================================================================
# Project (Singleton)
# =============================================================================


class Project:
    """Manages session file I/O with buffered async writes.

    This is a singleton class that manages buffered writes to the session
    transcript file. Writes are batched and flushed periodically or on demand.
    """

    _instance: Project | None = None

    def __init__(self) -> None:
        self.session_file: str | None = None
        self.current_session_title: str | None = None
        self.current_session_tag: str | None = None
        self.current_session_agent_name: str | None = None
        self.current_session_agent_color: str | None = None
        self.current_session_last_prompt: str | None = None
        self._write_queues: dict[str, list[tuple[Entry, Callable[[], None]]]] = {}
        self._flush_timer: Any = None
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> Project:
        """Get the singleton Project instance.

        Returns:
            The singleton Project instance.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset the singleton for testing.

        This should be called between tests to ensure isolation.
        """
        if cls._instance is not None:
            if cls._instance._flush_timer is not None:
                cls._instance._flush_timer.cancel()
            cls._instance = None

    def set_session_file(self, path: str | None) -> None:
        """Set the session file path.

        Args:
            path: Path to the session file.
        """
        self.session_file = path

    async def append_entry(self, entry: Entry) -> None:
        """Append an entry to the session file with buffering.

        Args:
            entry: The entry to append.
        """
        if self.session_file is None:
            return

        await self._ensure_directory()
        queue_key = self.session_file

        def resolve() -> None:
            pass

        if queue_key not in self._write_queues:
            self._write_queues[queue_key] = []
        self._write_queues[queue_key].append((entry, resolve))
        self._schedule_flush()

    async def flush(self) -> None:
        """Flush all pending writes to disk."""
        async with self._lock:
            for queue_key, entries in list(self._write_queues.items()):
                if not entries:
                    continue
                try:
                    with open(queue_key, "a", encoding="utf-8") as f:
                        for entry, _resolve in entries:
                            f.write(entry.to_jsonl())
                except OSError:
                    pass
            self._write_queues.clear()
            if self._flush_timer is not None:
                self._flush_timer.cancel()
                self._flush_timer = None

    async def remove_message_by_uuid(self, target_uuid: str) -> None:
        """Remove a message from transcript by UUID (tombstoning).

        This marks the message as deleted but preserves the file structure.

        Args:
            target_uuid: UUID of the message to remove.
        """
        if self.session_file is None:
            return

        if not os.path.exists(self.session_file):
            return

        try:
            file_size = os.path.getsize(self.session_file)
            if file_size > MAX_TOMBSTONE_REWRITE_BYTES:
                return

            with open(self.session_file, encoding="utf-8") as f:
                lines = f.readlines()

            new_lines: list[str] = []
            for line in lines:
                try:
                    entry_data = json.loads(line)
                    entry_uuid = entry_data.get("data", {}).get("uuid", "")
                    if entry_uuid == target_uuid:
                        entry_data["data"]["_tombstone"] = True
                        new_lines.append(json.dumps(entry_data) + "\n")
                    else:
                        new_lines.append(line)
                except (json.JSONDecodeError, KeyError):
                    new_lines.append(line)

            with open(self.session_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except OSError:
            pass

    def re_append_session_metadata(self) -> None:
        """Re-append cached metadata to session file tail.

        This is used when the session file is reopened and metadata
        needs to be refreshed.
        """
        pass  # Metadata re-append handled by append_entry

    async def _ensure_directory(self) -> None:
        """Ensure the session directory exists."""
        if self.session_file:
            directory = os.path.dirname(self.session_file)
            if directory:
                os.makedirs(directory, exist_ok=True)

    def _schedule_flush(self) -> None:
        """Schedule a flush in the background."""
        if self._flush_timer is not None:
            return

        def do_flush() -> None:
            asyncio.create_task(self.flush())

        self._flush_timer = asyncio.get_event_loop().call_later(0.5, do_flush)


# =============================================================================
# Agent Metadata Persistence
# =============================================================================


async def write_agent_metadata(
    agent_id: str,
    metadata: AgentMetadata,
) -> None:
    """Persist agent metadata for resume.

    Args:
        agent_id: The agent ID.
        metadata: The agent metadata.
    """
    projects_dir = get_projects_dir()
    metadata_dir = os.path.join(projects_dir, "agents")
    os.makedirs(metadata_dir, exist_ok=True)
    metadata_path = os.path.join(metadata_dir, f"{agent_id}.json")
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "agent_type": metadata.agent_type,
                    "worktree_path": metadata.worktree_path,
                    "description": metadata.description,
                },
                f,
            )
    except OSError:
        pass


async def read_agent_metadata(
    agent_id: str,
) -> AgentMetadata | None:
    """Read agent metadata.

    Args:
        agent_id: The agent ID.

    Returns:
        AgentMetadata if found, or None.
    """
    projects_dir = get_projects_dir()
    metadata_path = os.path.join(projects_dir, "agents", f"{agent_id}.json")
    try:
        with open(metadata_path, encoding="utf-8") as f:
            data = json.load(f)
            return AgentMetadata(
                agent_type=data["agent_type"],
                worktree_path=data.get("worktree_path"),
                description=data.get("description"),
            )
    except (OSError, KeyError, json.JSONDecodeError):
        return None


# =============================================================================
# Transcript Reading
# =============================================================================


# =============================================================================
# Worktree State Persistence
# =============================================================================


_worktree_state: dict[str, Any] | None = None


def save_worktree_state(state: dict[str, Any] | None) -> None:
    """Save or clear the current worktree state.

    Args:
        state: Worktree state dict, or None to clear.
    """
    global _worktree_state
    _worktree_state = state


def get_worktree_state() -> dict[str, Any] | None:
    """Get the saved worktree state."""
    return _worktree_state


# =============================================================================
# Transcript Reading
# =============================================================================


async def read_transcript_entries(
    session_id: str,
    limit: int | None = None,
) -> list[Entry]:
    """Read entries from a session transcript.

    Args:
        session_id: The session ID.
        limit: Maximum number of entries to read (from end).

    Returns:
        List of transcript entries.
    """
    path = get_transcript_path_for_session(session_id)
    if not os.path.exists(path):
        return []

    try:
        file_size = os.path.getsize(path)
        read_size = min(file_size, MAX_TRANSCRIPT_READ_BYTES)
        with open(path, "rb") as f:
            if file_size > MAX_TRANSCRIPT_READ_BYTES:
                f.seek(-read_size, 2)
                f.readline()
            content = f.read().decode("utf-8", errors="replace")

        lines = content.splitlines()
        entries: list[Entry] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(Entry.from_dict(data))
            except json.JSONDecodeError:
                continue

        if limit:
            return entries[-limit:]
        return entries
    except OSError:
        return []
