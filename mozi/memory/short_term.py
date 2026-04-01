"""Short-term memory implementation for the Mozi AI Coding Agent.

Short-term memory stores recent conversation context and is typically
backed by a vector store for similarity search.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ShortTermMemoryEntry:
    """A single entry in short-term memory.

    Attributes:
        id: Unique identifier for this entry.
        content: The content of the memory entry.
        timestamp: When this entry was created.
        metadata: Additional metadata for this entry.
    """

    id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class ShortTermMemory:
    """Short-term memory store for recent context.

    This class manages a sliding window of recent memory entries,
    automatically trimming old entries when the capacity is exceeded.

    Attributes:
        max_entries: Maximum number of entries to keep in memory.
        entries: Internal list of memory entries.
    """

    def __init__(self, max_entries: int = 100) -> None:
        """Initialize short-term memory.

        Args:
            max_entries: Maximum number of entries to retain.
                        Defaults to 100.
        """
        self.max_entries = max_entries
        self.entries: list[ShortTermMemoryEntry] = []

    def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ShortTermMemoryEntry:
        """Add a new entry to short-term memory.

        Args:
            content: The content to store in memory.
            metadata: Optional metadata to associate with this entry.

        Returns:
            The created memory entry.
        """
        entry_id = f"stm_{len(self.entries)}_{datetime.now().timestamp()}"
        entry = ShortTermMemoryEntry(
            id=entry_id,
            content=content,
            metadata=metadata or {},
        )
        self.entries.append(entry)

        if len(self.entries) > self.max_entries:
            self.trim(self.max_entries)

        return entry

    def get_recent(self, limit: int = 10) -> list[ShortTermMemoryEntry]:
        """Get the most recent memory entries.

        Args:
            limit: Maximum number of entries to return. Defaults to 10.

        Returns:
            List of the most recent memory entries, newest first.
        """
        if limit <= 0:
            return []
        return list(reversed(self.entries[-limit:]))

    def trim(self, max_entries: int | None = None) -> None:
        """Trim memory to keep only the most recent entries.

        Args:
            max_entries: Maximum entries to keep. If None, uses self.max_entries.
        """
        target = max_entries if max_entries is not None else self.max_entries
        if len(self.entries) > target:
            self.entries = self.entries[-target:]

    def clear(self) -> None:
        """Clear all entries from short-term memory."""
        self.entries.clear()

    def __len__(self) -> int:
        """Return the number of entries in memory."""
        return len(self.entries)

    def __repr__(self) -> str:
        """Return string representation of the memory."""
        return f"ShortTermMemory(entries={len(self.entries)}, max_entries={self.max_entries})"
