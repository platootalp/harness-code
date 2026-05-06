"""Markdown-based memory backend wrapping the existing file system."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.markdown.manager import add_memory_entry, list_memory_files, remove_memory_entry
from openharness.memory.markdown.memdir import load_memory_prompt
from openharness.memory.markdown.search import find_relevant_memories


class MarkdownMemoryBackend(MemoryBackend):
    """Memory backend that stores entries as markdown files."""

    def __init__(self, *, settings: object, cwd: str | Path) -> None:
        self.cwd = cwd
        mem = settings.memory  # type: ignore[attr-defined]
        self.max_entrypoint_lines: int = getattr(mem, "max_entrypoint_lines", 200)
        self.max_files: int = getattr(mem, "max_files", 5)

    async def add(
        self,
        content: str,
        *,
        title: str = "",
        memory_type: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        path = add_memory_entry(self.cwd, title or "memory", content)
        return MemoryEntry(
            id=path.name, title=title, content=content, memory_type=memory_type,
        )

    async def search(self, query: str, *, max_results: int = 5) -> list[MemoryEntry]:
        headers = find_relevant_memories(query, self.cwd, max_results=max_results)
        entries: list[MemoryEntry] = []
        for h in headers:
            try:
                text = h.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = h.body_preview
            entries.append(
                MemoryEntry(id=h.path.name, title=h.path.stem.replace("_", "-"), content=text, memory_type=h.memory_type),
            )
        return entries

    async def delete(self, id: str) -> bool:
        return remove_memory_entry(self.cwd, Path(id).stem)

    async def list_all(self, *, memory_type: str = "") -> list[MemoryEntry]:
        entries: list[MemoryEntry] = []
        for p in list_memory_files(self.cwd):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            entries.append(
                MemoryEntry(id=p.name, title=p.stem, content=text),
            )
        return entries

    def load_prompt_section(self, *, max_lines: int = 200) -> str | None:
        return load_memory_prompt(self.cwd, max_entrypoint_lines=max_lines)

    async def extract_and_store(self, messages: list[dict]) -> list[MemoryEntry]:
        return []  # Markdown backend: manual management only
