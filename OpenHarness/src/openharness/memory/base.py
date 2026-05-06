"""MemoryBackend protocol and MemoryEntry data model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryEntry:
    """Backend-agnostic memory entry."""

    id: str
    title: str
    content: str
    memory_type: str = ""
    metadata: dict[str, Any] | None = None
    score: float | None = None


class MemoryBackend(ABC):
    """Unified protocol for all memory backends."""

    @abstractmethod
    async def add(
        self,
        content: str,
        *,
        title: str = "",
        memory_type: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Add a memory entry."""

    @abstractmethod
    async def search(self, query: str, *, max_results: int = 5) -> list[MemoryEntry]:
        """Search for relevant memories."""

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""

    @abstractmethod
    async def list_all(self, *, memory_type: str = "") -> list[MemoryEntry]:
        """List all memories, optionally filtered by type."""

    @abstractmethod
    def load_prompt_section(self, *, max_lines: int = 200) -> str | None:
        """Load memory content for system prompt injection (sync, from cache)."""

    @abstractmethod
    async def extract_and_store(self, messages: list[dict]) -> list[MemoryEntry]:
        """Auto-extract memories from conversation messages."""

    def should_extract(
        self,
        *,
        message_count: int,
        elapsed_seconds: float,
        extract_every_n_messages: int,
        extract_every_seconds: float,
    ) -> bool:
        """Determine if extraction should run. Dual trigger: count OR time threshold."""
        return (
            message_count >= extract_every_n_messages
            or elapsed_seconds >= extract_every_seconds
        )
