"""Context offloader for Mozi.

Handles offloading and reloading of context data to external storage
when memory pressure is high.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mozi.context.models import BuiltContext, ContextConfig


@dataclass
class OffloadEntry:
    """An entry representing offloaded context data.

    Attributes:
        entry_id: Unique identifier for this entry.
        session_id: Associated session ID.
        context: The offloaded context data.
        offloaded_at: When the context was offloaded.
        access_count: Number of times this entry was accessed.
        last_accessed: Last access timestamp.
    """

    entry_id: str
    session_id: str
    context: dict[str, Any]
    offloaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now(UTC)


class Offloader:
    """Offloads context data to external storage.

    When context grows too large, parts of it can be offloaded
    to free up memory, with the ability to reload when needed.

    Attributes:
        config: Configuration for the offloader.
        _storage: Internal storage for offloaded entries.
    """

    DEFAULT_MAX_MEMORY_ENTRIES = 100
    DEFAULT_OFFLOAD_THRESHOLD = 0.9

    def __init__(
        self,
        config: ContextConfig | None = None,
        max_memory_entries: int | None = None,
    ) -> None:
        """Initialize the offloader.

        Args:
            config: Configuration for context building.
            max_memory_entries: Maximum entries to keep in memory.
        """
        self.config = config or ContextConfig()
        self._max_entries = max_memory_entries or self.DEFAULT_MAX_MEMORY_ENTRIES
        self._storage: dict[str, OffloadEntry] = {}

    @property
    def storage_size(self) -> int:
        """Get the current number of stored entries."""
        return len(self._storage)

    def should_offload(self, context: BuiltContext) -> bool:
        """Determine if the context should be offloaded.

        Args:
            context: The context to evaluate.

        Returns:
            True if offloading is recommended.
        """
        if self.storage_size >= self._max_entries:
            return True

        if context.total_tokens > self.config.max_tokens * self.DEFAULT_OFFLOAD_THRESHOLD:
            return True

        return False

    async def offload(
        self,
        session_id: str,
        context: BuiltContext,
    ) -> OffloadEntry:
        """Offload a context to external storage.

        Args:
            session_id: The session ID associated with this context.
            context: The context to offload.

        Returns:
            The created offload entry.
        """
        entry_id = f"offload_{session_id}_{datetime.now(UTC).timestamp()}"
        entry = OffloadEntry(
            entry_id=entry_id,
            session_id=session_id,
            context=context.to_dict(),
        )

        self._storage[entry_id] = entry
        return entry

    async def reload(self, entry_id: str) -> BuiltContext | None:
        """Reload a context from offloaded storage.

        Args:
            entry_id: The ID of the offload entry to reload.

        Returns:
            The reloaded context, or None if not found.
        """
        entry = self._storage.get(entry_id)
        if entry is None:
            return None

        entry.touch()

        context = BuiltContext(
            system_prompt=entry.context.get("system_prompt", ""),
            messages=entry.context.get("messages", []),
            memory_results=entry.context.get("memory_results", []),
            config=ContextConfig.from_dict(entry.context.get("config", {})),
            total_tokens=entry.context.get("total_tokens", 0),
            metadata=entry.context.get("metadata", {}),
        )

        return context

    async def reload_by_session(self, session_id: str) -> list[BuiltContext]:
        """Reload all contexts for a session.

        Args:
            session_id: The session ID to reload contexts for.

        Returns:
            List of reloaded contexts.
        """
        results: list[BuiltContext] = []
        for entry in self._storage.values():
            if entry.session_id == session_id:
                context = await self.reload(entry.entry_id)
                if context:
                    results.append(context)
        return results

    async def delete(self, entry_id: str) -> bool:
        """Delete an offload entry.

        Args:
            entry_id: The ID of the entry to delete.

        Returns:
            True if deleted, False if not found.
        """
        if entry_id in self._storage:
            del self._storage[entry_id]
            return True
        return False

    async def clear_session(self, session_id: str) -> int:
        """Clear all offload entries for a session.

        Args:
            session_id: The session ID to clear entries for.

        Returns:
            Number of entries cleared.
        """
        to_delete = [
            entry_id
            for entry_id, entry in self._storage.items()
            if entry.session_id == session_id
        ]
        for entry_id in to_delete:
            del self._storage[entry_id]
        return len(to_delete)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about offloaded data.

        Returns:
            Dictionary of offloader statistics.
        """
        total_access = sum(e.access_count for e in self._storage.values())
        return {
            "storage_size": self.storage_size,
            "max_entries": self._max_entries,
            "total_access_count": total_access,
            "oldest_entry": min((e.offloaded_at for e in self._storage.values()), default=None),
            "newest_entry": max((e.offloaded_at for e in self._storage.values()), default=None),
        }
