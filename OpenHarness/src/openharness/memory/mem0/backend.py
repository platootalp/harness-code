"""mem0-based memory backend with semantic search and auto-extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.mem0.config import _project_slug, build_local_config, check_mem0_available


class Mem0MemoryBackend(MemoryBackend):
    """Memory backend powered by mem0 for semantic search and auto-extraction."""

    def __init__(self, *, settings: object, cwd: str | Path) -> None:
        self.cwd = cwd
        mem = settings.memory  # type: ignore[attr-defined]
        self._mem0_settings = mem.mem0  # type: ignore[attr-defined]
        self._max_files: int = getattr(mem, "max_files", 5)
        self._max_entrypoint_lines: int = getattr(mem, "max_entrypoint_lines", 200)
        self._client: Any = None
        self._user_id: str = self._mem0_settings.extract_user_id
        self._auto_extract: bool = self._mem0_settings.auto_extract

        # Compute slug for cache path
        self._slug = _project_slug(cwd)
        from openharness.config.paths import get_data_dir
        cache_dir = get_data_dir() / "mem0_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path = cache_dir / f"{self._slug}.md"

    def _get_client(self) -> Any:
        """Lazily initialize and return the mem0 client."""
        if self._client is not None:
            return self._client

        check_mem0_available()

        if self._mem0_settings.storage == "local":
            from mem0 import Memory
            config = build_local_config(self._mem0_settings)
            self._client = Memory.from_config(config)
        elif self._mem0_settings.storage in ("cloud", "server"):
            from mem0 import MemoryClient
            self._client = MemoryClient(
                api_key=self._mem0_settings.api_key,
                base_url=self._mem0_settings.base_url,
            )
        else:
            raise ValueError(f"Unknown mem0 storage mode: {self._mem0_settings.storage}")
        return self._client

    async def add(
        self,
        content: str,
        *,
        title: str = "",
        memory_type: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        client = self._get_client()
        meta = {"title": title, "memory_type": memory_type, **(metadata or {})}
        result = client.add(content, user_id=self._user_id, metadata=meta)
        memories = result.get("results", []) if isinstance(result, dict) else []
        if memories:
            m = memories[0]
            return MemoryEntry(
                id=m.get("id", ""), title=title, content=m.get("memory", content),
                memory_type=memory_type,
            )
        return MemoryEntry(id="", title=title, content=content, memory_type=memory_type)

    async def search(self, query: str, *, max_results: int = 5) -> list[MemoryEntry]:
        client = self._get_client()
        results = client.search(query, user_id=self._user_id, limit=max_results)
        entries: list[MemoryEntry] = []
        for r in results:
            meta = r.get("metadata", {})
            entries.append(MemoryEntry(
                id=r.get("id", ""),
                title=meta.get("title", ""),
                content=r.get("memory", ""),
                memory_type=meta.get("memory_type", ""),
                metadata=meta,
                score=r.get("score"),
            ))
        return entries

    async def delete(self, id: str) -> bool:
        client = self._get_client()
        client.delete(id)
        return True

    async def list_all(self, *, memory_type: str = "") -> list[MemoryEntry]:
        client = self._get_client()
        results = client.get_all(user_id=self._user_id)
        if memory_type:
            results = [r for r in results if r.get("metadata", {}).get("memory_type") == memory_type]
        return [
            MemoryEntry(
                id=r.get("id", ""),
                title=r.get("metadata", {}).get("title", ""),
                content=r.get("memory", ""),
                memory_type=r.get("metadata", {}).get("memory_type", ""),
                metadata=r.get("metadata"),
            )
            for r in results
        ]

    def load_prompt_section(self, *, max_lines: int = 200) -> str | None:
        """Read the prompt cache file for system prompt injection."""
        if not self._cache_path.exists():
            return None
        try:
            text = self._cache_path.read_text(encoding="utf-8")
        except OSError:
            return None
        lines = text.splitlines()[:max_lines]
        if not lines:
            return None
        header = "# mem0 Memories"
        return f"{header}\n\n```md\n" + "\n".join(lines) + "\n```"

    async def extract_and_store(self, messages: list[dict]) -> list[MemoryEntry]:
        """Auto-extract memories from conversation messages via mem0."""
        if not self._auto_extract:
            return []
        client = self._get_client()
        result = client.add(messages, user_id=self._user_id)
        extracted: list[MemoryEntry] = []
        memories = result.get("results", []) if isinstance(result, dict) else []
        for m in memories:
            entry = MemoryEntry(
                id=m.get("id", ""),
                title="",
                content=m.get("memory", ""),
                memory_type=m.get("metadata", {}).get("memory_type", ""),
            )
            extracted.append(entry)
        self._update_prompt_cache(extracted)
        return extracted

    def _update_prompt_cache(self, entries: list[MemoryEntry]) -> None:
        """Write high-priority memories to the prompt cache file."""
        lines: list[str] = []
        for entry in entries:
            if entry.memory_type == "preference" or not entry.memory_type:
                label = entry.memory_type or "memory"
                lines.append(f"- [{label}] {entry.content}")
        if not lines:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass  # Cache is best-effort; don't block on write failures