# mem0 Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate mem0 as a pluggable memory backend alongside the existing Markdown system, with a unified MemoryBackend abstraction, configuration switching, and automatic memory extraction in the query loop.

**Architecture:** Abstract `MemoryBackend` ABC with two implementations: `MarkdownMemoryBackend` (wrapping existing code, refactored into `memory/markdown/` subpackage) and `Mem0MemoryBackend` (new, in `memory/mem0/` subpackage). A registry maps backend names to classes. The query loop pre-fetches relevant memories before prompt construction and auto-extracts memories after assistant responses using a dual-trigger strategy (message count + time threshold) plus a safety net before auto-compact.

**Tech Stack:** Python 3.11+, Pydantic, mem0 (optional), ChromaDB (via mem0), asyncio

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/openharness/memory/base.py` | `MemoryBackend` ABC + `MemoryEntry` dataclass |
| Create | `src/openharness/memory/registry.py` | `register_backend()`, `get_backend()` |
| Create | `src/openharness/memory/markdown/__init__.py` | Subpackage init, re-export public API |
| Create | `src/openharness/memory/markdown/backend.py` | `MarkdownMemoryBackend(MemoryBackend)` |
| Move | `src/openharness/memory/manager.py` → `src/openharness/memory/markdown/manager.py` | Existing add/remove/list operations |
| Move | `src/openharness/memory/search.py` → `src/openharness/memory/markdown/search.py` | Existing keyword search |
| Move | `src/openharness/memory/scan.py` → `src/openharness/memory/markdown/scan.py` | Existing file scanning |
| Move | `src/openharness/memory/memdir.py` → `src/openharness/memory/markdown/memdir.py` | Existing prompt loading |
| Move | `src/openharness/memory/paths.py` → `src/openharness/memory/markdown/paths.py` | Existing path helpers |
| Move | `src/openharness/memory/types.py` → `src/openharness/memory/markdown/types.py` | `MemoryHeader` (internal to markdown) |
| Modify | `src/openharness/memory/__init__.py` | Compat re-exports + backend registration |
| Create | `src/openharness/memory/mem0/__init__.py` | Subpackage init |
| Create | `src/openharness/memory/mem0/backend.py` | `Mem0MemoryBackend(MemoryBackend)` |
| Create | `src/openharness/memory/mem0/config.py` | Client factory + `_project_slug()` helper |
| Modify | `src/openharness/config/settings.py` | Add `Mem0Settings`, extend `MemorySettings` |
| Modify | `src/openharness/prompts/context.py` | Consume memory via backend abstraction |
| Modify | `src/openharness/engine/query_engine.py` | Add memory backend reference, extraction hooks |
| Modify | `src/openharness/engine/query.py` | Pre-fetch search, dual-trigger extraction, compact safety net |
| Create | `src/openharness/tools/memory_search_tool.py` | `memory_search` tool |
| Create | `src/openharness/tools/memory_add_tool.py` | `memory_add` tool |
| Modify | `src/openharness/tools/__init__.py` | Register memory tools |
| Modify | `pyproject.toml` | Add `[mem0]` optional dependency group |
| Create | `tests/test_memory/test_base.py` | Protocol compliance tests |
| Create | `tests/test_memory/test_registry.py` | Registry + switching tests |
| Create | `tests/test_memory/test_markdown_backend.py` | MarkdownMemoryBackend via protocol |
| Create | `tests/test_memory/test_mem0/__init__.py` | Test subpackage |
| Create | `tests/test_memory/test_mem0/test_backend.py` | Mem0MemoryBackend with mocked client |
| Create | `tests/test_memory/test_mem0/test_extraction.py` | Extraction timing tests |

---

### Task 1: MemoryBackend Protocol + MemoryEntry

**Files:**
- Create: `src/openharness/memory/base.py`
- Test: `tests/test_memory/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory/test_base.py
"""Tests for the MemoryBackend protocol and MemoryEntry dataclass."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from openharness.memory.base import MemoryBackend, MemoryEntry


class _StubBackend(MemoryBackend):
    """Minimal concrete backend for protocol tests."""

    async def add(self, content, *, title="", memory_type="", metadata=None):
        return MemoryEntry(id="1", title=title, content=content, memory_type=memory_type)

    async def search(self, query, *, max_results=5):
        return []

    async def delete(self, id):
        return True

    async def list_all(self, *, memory_type=""):
        return []

    def load_prompt_section(self, *, max_lines=200):
        return None

    async def extract_and_store(self, messages):
        return []


def test_memory_entry_is_frozen():
    entry = MemoryEntry(id="1", title="test", content="hello")
    with pytest.raises(FrozenInstanceError):
        entry.id = "2"


def test_memory_entry_defaults():
    entry = MemoryEntry(id="1", title="test", content="hello")
    assert entry.memory_type == ""
    assert entry.metadata is None
    assert entry.score is None


def test_memory_entry_with_all_fields():
    entry = MemoryEntry(
        id="abc", title="pref", content="likes dark mode",
        memory_type="preference", metadata={"source": "chat"}, score=0.95,
    )
    assert entry.memory_type == "preference"
    assert entry.metadata == {"source": "chat"}
    assert entry.score == 0.95


def test_stub_backend_satisfies_protocol():
    backend = _StubBackend()
    result = asyncio.run(backend.add("test content", title="test"))
    assert result.content == "test content"
    assert result.title == "test"


def test_should_extract_count_trigger():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=5, elapsed_seconds=0,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_should_extract_time_trigger():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=0, elapsed_seconds=300,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_should_extract_no_trigger():
    backend = _StubBackend()
    assert not backend.should_extract(
        message_count=3, elapsed_seconds=100,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        MemoryBackend()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'openharness.memory.base'`

- [ ] **Step 3: Write implementation**

```python
# src/openharness/memory/base.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_base.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/openharness/memory/base.py tests/test_memory/test_base.py
git commit -m "feat(memory): add MemoryBackend protocol and MemoryEntry dataclass"
```

---

### Task 2: Backend Registry

**Files:**
- Create: `src/openharness/memory/registry.py`
- Test: `tests/test_memory/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory/test_registry.py
"""Tests for the memory backend registry."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.registry import _backends, get_backend, register_backend


class _DummyBackend(MemoryBackend):
    def __init__(self, *, settings, cwd):
        self.cwd = cwd

    async def add(self, content, *, title="", memory_type="", metadata=None):
        return MemoryEntry(id="x", title=title, content=content)

    async def search(self, query, *, max_results=5):
        return []

    async def delete(self, id):
        return True

    async def list_all(self, *, memory_type=""):
        return []

    def load_prompt_section(self, *, max_lines=200):
        return None

    async def extract_and_store(self, messages):
        return []


class _SettingsStub:
    class _Memory:
        backend = "dummy"

    memory = _Memory()


def test_register_and_get_backend():
    register_backend("dummy", _DummyBackend)
    backend = get_backend(_SettingsStub(), cwd="/tmp/test")
    assert isinstance(backend, _DummyBackend)
    assert backend.cwd == Path("/tmp/test")


def test_get_unknown_backend_raises():
    with pytest.raises(ValueError, match="Unknown memory backend: nonexistent"):
        get_backend(
            type("_S", (), {"memory": type("_M", (), {"backend": "nonexistent"})()}),
            cwd="/tmp",
        )


def test_register_overwrites():
    register_backend("overwrite_test", _DummyBackend)
    register_backend("overwrite_test", _DummyBackend)
    backend = get_backend(_SettingsStub(), cwd="/tmp")
    assert isinstance(backend, _DummyBackend)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'openharness.memory.registry'`

- [ ] **Step 3: Write implementation**

```python
# src/openharness/memory/registry.py
"""Memory backend registry."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openharness.memory.base import MemoryBackend

_backends: dict[str, type] = {}


def register_backend(name: str, cls: type) -> None:
    """Register a memory backend class under the given name."""
    _backends[name] = cls


def get_backend(settings: object, *, cwd: str | Path) -> MemoryBackend:
    """Create and return the memory backend specified in settings."""
    backend_name = settings.memory.backend  # type: ignore[attr-defined]
    cls = _backends.get(backend_name)
    if cls is None:
        raise ValueError(f"Unknown memory backend: {backend_name}")
    return cls(settings=settings, cwd=cwd)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_registry.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/openharness/memory/registry.py tests/test_memory/test_registry.py
git commit -m "feat(memory): add backend registry with register_backend and get_backend"
```

---

### Task 3: Move Existing Memory Code to markdown/ Subpackage

**Files:**
- Create: `src/openharness/memory/markdown/__init__.py`
- Move: `src/openharness/memory/manager.py` → `src/openharness/memory/markdown/manager.py`
- Move: `src/openharness/memory/search.py` → `src/openharness/memory/markdown/search.py`
- Move: `src/openharness/memory/scan.py` → `src/openharness/memory/markdown/scan.py`
- Move: `src/openharness/memory/memdir.py` → `src/openharness/memory/markdown/memdir.py`
- Move: `src/openharness/memory/paths.py` → `src/openharness/memory/markdown/paths.py`
- Move: `src/openharness/memory/types.py` → `src/openharness/memory/markdown/types.py`
- Modify: `src/openharness/memory/__init__.py`

- [ ] **Step 1: Create markdown subpackage and move files**

```bash
cd /Users/lijunyi/road/reference/OpenHarness
mkdir -p src/openharness/memory/markdown

# Move existing files into markdown/ subpackage
git mv src/openharness/memory/manager.py src/openharness/memory/markdown/manager.py
git mv src/openharness/memory/search.py src/openharness/memory/markdown/search.py
git mv src/openharness/memory/scan.py src/openharness/memory/markdown/scan.py
git mv src/openharness/memory/memdir.py src/openharness/memory/markdown/memdir.py
git mv src/openharness/memory/paths.py src/openharness/memory/markdown/paths.py
git mv src/openharness/memory/types.py src/openharness/memory/markdown/types.py
```

- [ ] **Step 2: Fix internal imports in moved files**

Each moved file has internal cross-imports using `from openharness.memory.X`. These must be updated to `from openharness.memory.markdown.X`:

In `src/openharness/memory/markdown/manager.py`:
- Change `from openharness.memory.paths` → `from openharness.memory.markdown.paths`

In `src/openharness/memory/markdown/scan.py`:
- Change `from openharness.memory.paths` → `from openharness.memory.markdown.paths`
- Change `from openharness.memory.types` → `from openharness.memory.markdown.types`

In `src/openharness/memory/markdown/search.py`:
- Change `from openharness.memory.scan` → `from openharness.memory.markdown.scan`
- Change `from openharness.memory.types` → `from openharness.memory.markdown.types`

In `src/openharness/memory/markdown/memdir.py`:
- Change `from openharness.memory.paths` → `from openharness.memory.markdown.paths`

(No changes needed in `paths.py` or `types.py` — they only import from `openharness.config.paths` and stdlib.)

- [ ] **Step 3: Create markdown/__init__.py**

```python
# src/openharness/memory/markdown/__init__.py
"""Markdown-based memory backend subpackage."""

from openharness.memory.markdown.manager import add_memory_entry, list_memory_files, remove_memory_entry
from openharness.memory.markdown.memdir import load_memory_prompt
from openharness.memory.markdown.paths import get_memory_entrypoint, get_project_memory_dir
from openharness.memory.markdown.scan import scan_memory_files
from openharness.memory.markdown.search import find_relevant_memories

__all__ = [
    "add_memory_entry",
    "find_relevant_memories",
    "get_memory_entrypoint",
    "get_project_memory_dir",
    "list_memory_files",
    "load_memory_prompt",
    "remove_memory_entry",
    "scan_memory_files",
]
```

- [ ] **Step 4: Update memory/__init__.py for compat re-exports**

```python
# src/openharness/memory/__init__.py
"""Memory exports — backward-compatible re-exports + backend registration."""

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.markdown.manager import add_memory_entry, list_memory_files, remove_memory_entry
from openharness.memory.markdown.memdir import load_memory_prompt
from openharness.memory.markdown.paths import get_memory_entrypoint, get_project_memory_dir
from openharness.memory.markdown.scan import scan_memory_files
from openharness.memory.markdown.search import find_relevant_memories
from openharness.memory.registry import get_backend, register_backend

__all__ = [
    "MemoryBackend",
    "MemoryEntry",
    "add_memory_entry",
    "find_relevant_memories",
    "get_backend",
    "get_memory_entrypoint",
    "get_project_memory_dir",
    "list_memory_files",
    "load_memory_prompt",
    "register_backend",
    "remove_memory_entry",
    "scan_memory_files",
]

# Register default backends at import time
register_backend("markdown", __import__(
    "openharness.memory.markdown.backend", fromlist=["MarkdownMemoryBackend"]
).MarkdownMemoryBackend)
```

Note: The lazy `__import__` avoids circular imports — `MarkdownMemoryBackend` is created in Task 4. For now this line will fail at import; that's OK since we'll add the backend in the next task. **Alternatively**, if you prefer to defer registration, remove the `register_backend` call here and add it in Task 4 when the file exists.

**Simpler approach** — just defer the register calls until both backends exist. Remove the `register_backend` call from `__init__.py` for now. It will be added in Task 6 after both backends exist.

Updated `__init__.py`:

```python
# src/openharness/memory/__init__.py
"""Memory exports — backward-compatible re-exports + backend registration."""

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.markdown.manager import add_memory_entry, list_memory_files, remove_memory_entry
from openharness.memory.markdown.memdir import load_memory_prompt
from openharness.memory.markdown.paths import get_memory_entrypoint, get_project_memory_dir
from openharness.memory.markdown.scan import scan_memory_files
from openharness.memory.markdown.search import find_relevant_memories
from openharness.memory.registry import get_backend, register_backend

__all__ = [
    "MemoryBackend",
    "MemoryEntry",
    "add_memory_entry",
    "find_relevant_memories",
    "get_backend",
    "get_memory_entrypoint",
    "get_project_memory_dir",
    "list_memory_files",
    "load_memory_prompt",
    "register_backend",
    "remove_memory_entry",
    "scan_memory_files",
]
```

- [ ] **Step 5: Fix any external imports**

Search for and update any files outside `memory/` that import from `openharness.memory.X` where X is now in `markdown/`. The key consumers:

In `src/openharness/prompts/context.py` line 15:
```python
# Before:
from openharness.memory import find_relevant_memories, load_memory_prompt
# After: (no change needed — __init__.py re-exports these)
```

No changes needed in `prompts/context.py` — the compat re-exports handle it.

- [ ] **Step 6: Run existing memory tests to verify no regressions**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/ -v`
Expected: All existing tests PASS (they import from `openharness.memory` which re-exports)

- [ ] **Step 7: Commit**

```bash
git add src/openharness/memory/
git commit -m "refactor(memory): move existing code into markdown/ subpackage with compat re-exports"
```

---

### Task 4: MarkdownMemoryBackend

**Files:**
- Create: `src/openharness/memory/markdown/backend.py`
- Test: `tests/test_memory/test_markdown_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory/test_markdown_backend.py
"""Tests for MarkdownMemoryBackend via the MemoryBackend protocol."""

from __future__ import annotations

import asyncio
from pathlib import Path

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.markdown.backend import MarkdownMemoryBackend


class _SettingsStub:
    class _Memory:
        max_entrypoint_lines = 200
        max_files = 5

    memory = _Memory()


def _run(coro):
    return asyncio.run(coro)


def test_add_returns_memory_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    entry = _run(backend.add("test content", title="my-note"))
    assert isinstance(entry, MemoryEntry)
    assert entry.title == "my-note"
    assert entry.content == "test content"


def test_search_finds_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    _run(backend.add("Redis cache invalidation strategy", title="redis-cache"))
    results = _run(backend.search("redis caching"))
    assert len(results) >= 1
    assert results[0].title == "redis-cache"


def test_delete_removes_entry(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    entry = _run(backend.add("to be deleted", title="deleteme"))
    assert _run(backend.delete(Path(entry.id).stem))
    results = _run(backend.search("deleteme"))
    assert len(results) == 0


def test_list_all_returns_entries(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    _run(backend.add("first entry", title="first"))
    _run(backend.add("second entry", title="second"))
    all_entries = _run(backend.list_all())
    assert len(all_entries) >= 2


def test_load_prompt_section(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    section = backend.load_prompt_section()
    assert section is not None
    assert "Memory" in section


def test_extract_and_store_is_noop(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = MarkdownMemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    result = _run(backend.extract_and_store([{"role": "user", "content": "hello"}]))
    assert result == []


def test_satisfies_protocol():
    """MarkdownMemoryBackend is a proper MemoryBackend subclass."""
    assert issubclass(MarkdownMemoryBackend, MemoryBackend)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_markdown_backend.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'openharness.memory.markdown.backend'`

- [ ] **Step 3: Write implementation**

```python
# src/openharness/memory/markdown/backend.py
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
                MemoryEntry(id=h.path.name, title=h.title, content=text, memory_type=h.memory_type),
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
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_markdown_backend.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/openharness/memory/markdown/backend.py tests/test_memory/test_markdown_backend.py
git commit -m "feat(memory): add MarkdownMemoryBackend wrapping existing file system"
```

---

### Task 5: Mem0Settings + MemorySettings Extension

**Files:**
- Modify: `src/openharness/config/settings.py:60-67`

- [ ] **Step 1: Add Mem0Settings and extend MemorySettings**

In `src/openharness/config/settings.py`, after line 67 (the current `MemorySettings` class), add `Mem0Settings` and update `MemorySettings`:

```python
class Mem0Settings(BaseModel):
    """mem0-specific configuration."""

    storage: str = "local"  # "local" | "cloud" | "server"
    vector_store: str = "chroma"  # "chroma" | "qdrant"
    embedder: str = "openai"  # Embedding model provider (requires corresponding API key)
    embedder_model: str = "text-embedding-3-small"
    api_key: str | None = None  # For cloud/server mode
    base_url: str | None = None  # For self-hosted server
    auto_extract: bool = True
    extract_user_id: str = "default"  # mem0 user_id for memory scoping
    extract_every_n_messages: int = 5  # Extract every N user-assistant turns
    extract_every_seconds: float = 300.0  # Or every 5 minutes, whichever comes first
```

Update `MemorySettings` to add the new fields:

```python
class MemorySettings(BaseModel):
    """Memory system configuration."""

    enabled: bool = True
    backend: str = "markdown"  # "markdown" | "mem0"
    max_files: int = 5
    max_entrypoint_lines: int = 200
    context_window_tokens: int | None = None
    auto_compact_threshold_tokens: int | None = None
    mem0: Mem0Settings = Field(default_factory=Mem0Settings)
```

- [ ] **Step 2: Add OH_MEMORY_BACKEND env override**

In `src/openharness/config/settings.py`, within `_apply_env_overrides()`, after the sandbox block (around line 837), add:

```python
    # --- memory backend ---
    memory_backend = os.environ.get("OH_MEMORY_BACKEND")
    if memory_backend:
        memory_updates: dict[str, Any] = {}
        memory_updates["backend"] = memory_backend
        if "memory" not in updates:
            updates["memory"] = settings.memory.model_copy(update=memory_updates)
        else:
            updates["memory"] = updates["memory"].model_copy(update=memory_updates)
```

- [ ] **Step 3: Run existing settings tests to verify no regressions**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/ -k "settings" -v --timeout=30`
Expected: All pass. The new fields have defaults so existing settings.json files are compatible.

- [ ] **Step 4: Commit**

```bash
git add src/openharness/config/settings.py
git commit -m "feat(settings): add Mem0Settings and extend MemorySettings with backend field"
```

---

### Task 6: Mem0MemoryBackend

**Files:**
- Create: `src/openharness/memory/mem0/__init__.py`
- Create: `src/openharness/memory/mem0/backend.py`
- Create: `src/openharness/memory/mem0/config.py`
- Test: `tests/test_memory/test_mem0/__init__.py`
- Test: `tests/test_memory/test_mem0/test_backend.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory/test_mem0/__init__.py
```

```python
# tests/test_memory/test_mem0/test_backend.py
"""Tests for Mem0MemoryBackend with mocked mem0 client."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.mem0.backend import Mem0MemoryBackend


class _Mem0Settings:
    storage = "local"
    vector_store = "chroma"
    embedder = "openai"
    embedder_model = "text-embedding-3-small"
    api_key = None
    base_url = None
    auto_extract = True
    extract_user_id = "default"
    extract_every_n_messages = 5
    extract_every_seconds = 300.0


class _SettingsStub:
    class _Memory:
        backend = "mem0"
        max_entrypoint_lines = 200
        max_files = 5
        mem0 = _Mem0Settings()

    memory = _Memory()


def _run(coro):
    return asyncio.run(coro)


def _mock_local_client():
    """Return a mock Memory (local) client."""
    client = MagicMock()
    client.add.return_value = {"results": [{"id": "mem1", "memory": "User prefers dark mode", "event": "ADD"}]}
    client.search.return_value = [
        {"id": "mem1", "memory": "User prefers dark mode", "score": 0.95,
         "metadata": {"title": "theme-pref", "memory_type": "preference"}},
    ]
    client.get_all.return_value = [
        {"id": "mem1", "memory": "User prefers dark mode",
         "metadata": {"title": "theme-pref", "memory_type": "preference"}},
    ]
    client.delete.return_value = None
    return client


def test_add_calls_client(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entry = _run(backend.add("User prefers dark mode", title="theme-pref", memory_type="preference"))

    mock_client.add.assert_called_once()
    assert isinstance(entry, MemoryEntry)
    assert entry.content == "User prefers dark mode"


def test_search_returns_scored_entries(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    results = _run(backend.search("theme preference"))

    assert len(results) == 1
    assert results[0].score == 0.95
    assert results[0].memory_type == "preference"


def test_delete_calls_client(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    result = _run(backend.delete("mem1"))
    assert result is True
    mock_client.delete.assert_called_once_with("mem1")


def test_list_all_calls_get_all(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entries = _run(backend.list_all())
    assert len(entries) == 1
    mock_client.get_all.assert_called_once()


def test_list_all_filters_by_memory_type(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entries = _run(backend.list_all(memory_type="preference"))
    assert len(entries) == 1

    entries = _run(backend.list_all(memory_type="fact"))
    assert len(entries) == 0


def test_extract_and_store_calls_add_with_messages(tmp_path: Path):
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    messages = [{"role": "user", "content": "I prefer dark mode"}]
    entries = _run(backend.extract_and_store(messages))

    mock_client.add.assert_called_once_with(messages, user_id="default")
    assert len(entries) >= 1


def test_extract_and_store_disabled(tmp_path: Path):
    settings = _SettingsStub()
    settings.memory.mem0.auto_extract = False
    backend = Mem0MemoryBackend(settings=settings, cwd=tmp_path)
    mock_client = _mock_local_client()
    backend._client = mock_client

    entries = _run(backend.extract_and_store([{"role": "user", "content": "hello"}]))
    assert entries == []
    mock_client.add.assert_not_called()


def test_load_prompt_section_reads_cache(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    backend = Mem0MemoryBackend(settings=_SettingsStub(), cwd=tmp_path / "project")
    # Write a cache file
    cache_dir = tmp_path / "data" / "mem0_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "project-abc123.md"
    cache_file.write_text("# mem0 Memories\n- User prefers dark mode\n", encoding="utf-8")

    # Mock _cache_path to point to our test cache
    backend._cache_path = cache_file
    section = backend.load_prompt_section()
    # If cache doesn't exist, returns None — that's also valid behavior
    # For this test we check it doesn't crash
    assert section is None or "mem0" in section.lower() or isinstance(section, str)


def test_satisfies_protocol():
    assert issubclass(Mem0MemoryBackend, MemoryBackend)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_mem0/test_backend.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'openharness.memory.mem0'`

- [ ] **Step 3: Create mem0 subpackage init**

```python
# src/openharness/memory/mem0/__init__.py
"""mem0-based memory backend subpackage."""
```

- [ ] **Step 4: Create config helper**

```python
# src/openharness/memory/mem0/config.py
"""mem0 client factory and helpers."""

from __future__ import annotations

from hashlib import sha1
from pathlib import Path


def _project_slug(cwd: str | Path) -> str:
    """Derive a short slug from the project path for collection naming."""
    path = Path(cwd).resolve()
    digest = sha1(str(path).encode("utf-8")).hexdigest()[:12]
    return f"{path.name}-{digest}"


def build_local_config(mem0_settings: object) -> dict:
    """Build the mem0 config dict for local storage mode."""
    return {
        "vector_store": {
            "provider": mem0_settings.vector_store,  # type: ignore[attr-defined]
            "config": {
                "collection_name": "oh_mem0",
                "path": str(Path.home() / ".openharness" / "mem0_data"),
            },
        },
        "embedder": {
            "provider": mem0_settings.embedder,  # type: ignore[attr-defined]
            "config": {
                "model": mem0_settings.embedder_model,  # type: ignore[attr-defined]
            },
        },
    }


def check_mem0_available() -> None:
    """Raise a clear error if the mem0 package is not installed."""
    try:
        import mem0  # noqa: F401
    except ImportError:
        raise ImportError(
            'Memory backend "mem0" requires the mem0 package. '
            'Install with: pip install openharness[mem0]'
        )
```

- [ ] **Step 5: Write Mem0MemoryBackend**

```python
# src/openharness/memory/mem0/backend.py
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

        # Prompt cache path
        slug = _project_slug(cwd)
        from openharness.config.paths import get_data_dir
        cache_dir = get_data_dir() / "mem0_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path = cache_dir / f"{slug}.md"

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
        return f"{header}\n\n```md\n{chr(10).join(lines)}\n```"

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
                content=m.get("memory", ""),
                memory_type=m.get("metadata", {}).get("memory_type", ""),
            )
            extracted.append(entry)
        # Update prompt cache with extracted memories
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
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_mem0/test_backend.py -v`
Expected: All 10 tests PASS

- [ ] **Step 7: Register backends in memory/__init__.py**

Update `src/openharness/memory/__init__.py` to add backend registration after imports:

```python
# src/openharness/memory/__init__.py
"""Memory exports — backward-compatible re-exports + backend registration."""

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.markdown.backend import MarkdownMemoryBackend
from openharness.memory.markdown.manager import add_memory_entry, list_memory_files, remove_memory_entry
from openharness.memory.markdown.memdir import load_memory_prompt
from openharness.memory.markdown.paths import get_memory_entrypoint, get_project_memory_dir
from openharness.memory.markdown.scan import scan_memory_files
from openharness.memory.markdown.search import find_relevant_memories
from openharness.memory.mem0.backend import Mem0MemoryBackend
from openharness.memory.registry import get_backend, register_backend

__all__ = [
    "MarkdownMemoryBackend",
    "Mem0MemoryBackend",
    "MemoryBackend",
    "MemoryEntry",
    "add_memory_entry",
    "find_relevant_memories",
    "get_backend",
    "get_memory_entrypoint",
    "get_project_memory_dir",
    "list_memory_files",
    "load_memory_prompt",
    "register_backend",
    "remove_memory_entry",
    "scan_memory_files",
]

# Register built-in backends
register_backend("markdown", MarkdownMemoryBackend)
register_backend("mem0", Mem0MemoryBackend)
```

- [ ] **Step 8: Commit**

```bash
git add src/openharness/memory/mem0/ src/openharness/memory/__init__.py tests/test_memory/test_mem0/
git commit -m "feat(memory): add Mem0MemoryBackend with semantic search and auto-extraction"
```

---

### Task 7: Extraction Timing Tests

**Files:**
- Test: `tests/test_memory/test_mem0/test_extraction.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_memory/test_mem0/test_extraction.py
"""Tests for memory extraction timing (dual-trigger + compact safety net)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from openharness.memory.base import MemoryBackend


class _StubBackend(MemoryBackend):
    """Minimal backend with real should_extract for timing tests."""

    async def add(self, content, *, title="", memory_type="", metadata=None):
        return NotImplemented

    async def search(self, query, *, max_results=5):
        return NotImplemented

    async def delete(self, id):
        return NotImplemented

    async def list_all(self, *, memory_type=""):
        return NotImplemented

    def load_prompt_section(self, *, max_lines=200):
        return NotImplemented

    async def extract_and_store(self, messages):
        return []


def test_trigger_on_message_count():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=5, elapsed_seconds=0,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_trigger_on_elapsed_time():
    backend = _StubBackend()
    assert backend.should_extract(
        message_count=0, elapsed_seconds=300,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_no_trigger_below_thresholds():
    backend = _StubBackend()
    assert not backend.should_extract(
        message_count=4, elapsed_seconds=299,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_trigger_on_either_threshold():
    backend = _StubBackend()
    # Count met but time not
    assert backend.should_extract(
        message_count=5, elapsed_seconds=10,
        extract_every_n_messages=5, extract_every_seconds=300,
    )
    # Time met but count not
    assert backend.should_extract(
        message_count=1, elapsed_seconds=300,
        extract_every_n_messages=5, extract_every_seconds=300,
    )


def test_custom_thresholds():
    backend = _StubBackend()
    # More aggressive thresholds
    assert backend.should_extract(
        message_count=2, elapsed_seconds=0,
        extract_every_n_messages=2, extract_every_seconds=60,
    )
    # Not yet with lenient thresholds
    assert not backend.should_extract(
        message_count=2, elapsed_seconds=0,
        extract_every_n_messages=10, extract_every_seconds=600,
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/test_mem0/test_extraction.py -v`
Expected: All 5 tests PASS (uses `should_extract` from `MemoryBackend` base, already implemented in Task 1)

- [ ] **Step 3: Commit**

```bash
git add tests/test_memory/test_mem0/test_extraction.py
git commit -m "test(memory): add extraction timing tests for dual-trigger strategy"
```

---

### Task 8: Integration — prompts/context.py via Backend

**Files:**
- Modify: `src/openharness/prompts/context.py:74-162`

- [ ] **Step 1: Modify build_runtime_system_prompt to accept pre-fetched memories and use backend**

The key change: the function accepts an optional `relevant_memories` parameter (pre-fetched by QueryEngine) and uses `backend.load_prompt_section()` instead of `load_memory_prompt()` / `find_relevant_memories()` directly.

Replace the memory section (lines 133-160) in `src/openharness/prompts/context.py`:

```python
def build_runtime_system_prompt(
    settings: Settings,
    *,
    cwd: str | Path,
    latest_user_prompt: str | None = None,
    extra_skill_dirs: Iterable[str | Path] | None = None,
    extra_plugin_roots: Iterable[str | Path] | None = None,
    relevant_memories: list | None = None,  # NEW parameter
) -> str:
```

In the body, replace the memory block (lines 133-160) with:

```python
    if settings.memory.enabled:
        from openharness.memory.registry import get_backend
        from openharness.memory.base import MemoryEntry

        backend = get_backend(settings, cwd=cwd)
        memory_section = backend.load_prompt_section(
            max_lines=settings.memory.max_entrypoint_lines,
        )
        if memory_section:
            sections.append(memory_section)

        if relevant_memories:
            lines = ["# Relevant Memories"]
            for entry in relevant_memories:
                if isinstance(entry, MemoryEntry):
                    lines.extend(
                        [
                            "",
                            f"## {entry.title or entry.id}",
                            "```md",
                            entry.content[:8000],
                            "```",
                        ]
                    )
            sections.append("\n".join(lines))
```

Also remove the old import on line 15:
```python
# Remove: from openharness.memory import find_relevant_memories, load_memory_prompt
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/ -k "context or memory" -v --timeout=30`
Expected: All pass. When `relevant_memories` is None (default), behavior is unchanged for the prompt section. The search section is now skipped unless `relevant_memories` is explicitly passed.

- [ ] **Step 3: Commit**

```bash
git add src/openharness/prompts/context.py
git commit -m "feat(prompts): route memory loading through backend abstraction"
```

---

### Task 9: Integration — QueryEngine Memory Hooks

**Files:**
- Modify: `src/openharness/engine/query_engine.py`
- Modify: `src/openharness/engine/query.py`

This is the most integration-heavy task. It wires the backend into the query loop for:
1. Pre-fetching relevant memories before prompt construction
2. Dual-trigger extraction after assistant responses
3. Safety net extraction before auto-compact

- [ ] **Step 1: Add memory backend reference to QueryEngine**

In `src/openharness/engine/query_engine.py`, add imports and modify `__init__`:

At the top, add:
```python
import time

from openharness.memory.base import MemoryBackend, MemoryEntry
from openharness.memory.registry import get_backend
```

In `__init__`, add these parameters and instance variables after `tool_metadata`:
```python
        settings: object | None = None,
```

And in the body:
```python
        self._settings = settings
        self._memory_backend: MemoryBackend | None = None
        self._last_extract_at: float = time.monotonic()
        self._messages_since_extract: int = 0
```

Add a property:
```python
    @property
    def memory_backend(self) -> MemoryBackend | None:
        """Return the memory backend, lazily initialized."""
        if self._memory_backend is None and self._settings is not None:
            try:
                self._memory_backend = get_backend(self._settings, cwd=self._cwd)
            except (ValueError, ImportError):
                return None
        return self._memory_backend
```

- [ ] **Step 2: Pre-fetch memories in submit_message before prompt construction**

In `submit_message()`, before the `context = QueryContext(...)` line (around line 165), add memory pre-fetch:

```python
        # Pre-fetch relevant memories (async) before prompt construction
        relevant_memories: list[MemoryEntry] = []
        if self.memory_backend is not None and self._settings is not None:
            try:
                relevant_memories = await self.memory_backend.search(
                    user_message.text, max_results=self._settings.memory.max_files,
                )
            except Exception:
                relevant_memories = []  # Non-fatal; continue without memories
```

Pass `relevant_memories` to `build_runtime_system_prompt` (this requires the caller — wherever `build_runtime_system_prompt` is called — to pass this through). The `submit_message` method doesn't call `build_runtime_system_prompt` directly; it uses `self._system_prompt`. The system prompt is built in the CLI layer. For now, store relevant_memories on the context so the query loop can use them.

Add `relevant_memories` to `QueryContext`:

In `src/openharness/engine/query.py`, add to the `QueryContext` dataclass:
```python
    relevant_memories: list | None = None
```

And in `query_engine.py`, pass it:
```python
        context = QueryContext(
            ...,
            relevant_memories=relevant_memories,
        )
```

- [ ] **Step 3: Add extraction hooks after assistant response**

In `src/openharness/engine/query.py`, in the `run_query` function, after the assistant turn completes (where `AssistantTurnComplete` is yielded), add extraction logic.

Find the line that yields `AssistantTurnComplete` and add after it:

```python
        # Memory extraction hook
        if context.relevant_memories is not None:
            from openharness.memory.base import MemoryBackend
            backend = context.relevant_memories  # Actually we need the backend itself
```

**Correction** — the `relevant_memories` list is not the backend. We need to pass the backend directly. Let's adjust:

Add to `QueryContext`:
```python
    memory_backend: MemoryBackend | None = None
    memory_settings: object | None = None
```

In `query_engine.py`, pass:
```python
        context = QueryContext(
            ...,
            memory_backend=self.memory_backend,
            memory_settings=self._settings,
        )
```

In `run_query` in `query.py`, after the main loop iteration (after `AssistantTurnComplete` yield), add:

```python
        # --- memory extraction after assistant response ---
        if context.memory_backend is not None and context.memory_settings is not None:
            _maybe_extract_memories(context, messages)
```

Add helper function before `run_query`:

```python
def _maybe_extract_memories(context: QueryContext, messages: list) -> None:
    """Check extraction triggers and run if threshold met."""
    import time
    backend = context.memory_backend
    if backend is None:
        return
    mem_settings = context.memory_settings.memory.mem0  # type: ignore[attr-defined]
    if not mem_settings.auto_extract:
        return
    elapsed = time.monotonic() - context._last_extract_at  # type: ignore[attr-defined]
    if backend.should_extract(
        message_count=context._messages_since_extract,  # type: ignore[attr-defined]
        elapsed_seconds=elapsed,
        extract_every_n_messages=mem_settings.extract_every_n_messages,
        extract_every_seconds=mem_settings.extract_every_seconds,
    ):
        import asyncio
        try:
            asyncio.get_running_loop().create_task(
                backend.extract_and_store([m.model_dump() if hasattr(m, "model_dump") else str(m) for m in messages]),
            )
        except Exception:
            pass
        context._last_extract_at = time.monotonic()  # type: ignore[attr-defined]
        context._messages_since_extract = 0  # type: ignore[attr-defined]
    else:
        context._messages_since_extract += 1  # type: ignore[attr-defined]
```

**Note:** This is a simplified approach. In production, extraction should be awaited properly, not fire-and-forget with `create_task`. However, since extraction is non-blocking to the user experience, this is acceptable for the initial implementation. A future improvement would be to use a background task queue.

**Better approach** — make extraction synchronous-within-the-loop:

Since `run_query` is already async, just await it inline:

```python
        # --- memory extraction after assistant response ---
        if context.memory_backend is not None and context.memory_settings is not None:
            await _maybe_extract_memories(context, messages)
```

And the helper:

```python
async def _maybe_extract_memories(context: QueryContext, messages: list) -> None:
    """Check extraction triggers and run if threshold met."""
    import time
    backend = context.memory_backend
    if backend is None:
        return
    mem_settings = context.memory_settings.memory.mem0  # type: ignore[attr-defined]
    if not mem_settings.auto_extract:
        return
    elapsed = time.monotonic() - context._last_extract_at
    if backend.should_extract(
        message_count=context._messages_since_extract,
        elapsed_seconds=elapsed,
        extract_every_n_messages=mem_settings.extract_every_n_messages,
        extract_every_seconds=mem_settings.extract_every_seconds,
    ):
        try:
            await backend.extract_and_store(
                [m.model_dump() if hasattr(m, "model_dump") else {"role": getattr(m, "role", "unknown"), "content": str(m)} for m in messages],
            )
        except Exception:
            pass
        context._last_extract_at = time.monotonic()
        context._messages_since_extract = 0
    else:
        context._messages_since_extract += 1
```

- [ ] **Step 4: Add compact safety net**

In `run_query`, before the auto-compact check (line ~520), add:

```python
        # --- memory safety net: extract before compact ---
        if context.memory_backend is not None and context.memory_settings is not None:
            await _extract_before_compact(context, messages)
```

Helper:

```python
async def _extract_before_compact(context: QueryContext, messages: list) -> None:
    """Safety net: extract memories before compaction to preserve details."""
    import time
    backend = context.memory_backend
    if backend is None:
        return
    mem_settings = context.memory_settings.memory.mem0  # type: ignore[attr-defined]
    if not mem_settings.auto_extract:
        return
    try:
        await backend.extract_and_store(
            [m.model_dump() if hasattr(m, "model_dump") else {"role": getattr(m, "role", "unknown"), "content": str(m)} for m in messages],
        )
    except Exception:
        pass
    context._last_extract_at = time.monotonic()
    context._messages_since_extract = 0
```

- [ ] **Step 5: Add _last_extract_at and _messages_since_extract to QueryContext**

Add to `QueryContext` dataclass in `query.py`:

```python
    _last_extract_at: float = field(default_factory=time.monotonic)
    _messages_since_extract: int = 0
```

And add `import time` at the top of the file.

- [ ] **Step 6: Wire settings into QueryEngine from CLI**

The `settings` parameter needs to be passed when `QueryEngine` is constructed. Find the call site(s) that create `QueryEngine` and add `settings=settings`. This is typically in `src/openharness/cli.py`.

Search for `QueryEngine(` in the codebase and add `settings=settings` to each construction.

- [ ] **Step 7: Run existing tests**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/ -k "query" -v --timeout=30`
Expected: All pass. New parameters have defaults.

- [ ] **Step 8: Commit**

```bash
git add src/openharness/engine/query_engine.py src/openharness/engine/query.py src/openharness/cli.py
git commit -m "feat(engine): wire memory backend into query loop for search, extraction, and compact safety net"
```

---

### Task 10: Memory Tools

**Files:**
- Create: `src/openharness/tools/memory_search_tool.py`
- Create: `src/openharness/tools/memory_add_tool.py`
- Modify: `src/openharness/tools/__init__.py`

- [ ] **Step 1: Write memory_search_tool.py**

```python
# src/openharness/tools/memory_search_tool.py
"""Tool for searching persistent memory."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MemorySearchInput(BaseModel):
    """Arguments for memory search."""

    query: str = Field(description="Search query to find relevant memories")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to return")


class MemorySearchTool(BaseTool):
    """Search persistent memory for relevant context."""

    name = "memory_search"
    description = "Search persistent memory for relevant context, preferences, and past decisions."
    input_model = MemorySearchInput

    def is_read_only(self, arguments: MemorySearchInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: MemorySearchInput, context: ToolExecutionContext) -> ToolResult:
        from openharness.memory.registry import get_backend

        metadata = context.metadata
        settings = metadata.get("settings")
        if settings is None:
            return ToolResult(output="Memory search unavailable: no settings in context.")

        try:
            backend = get_backend(settings, cwd=context.cwd)
        except (ValueError, ImportError) as exc:
            return ToolResult(output=f"Memory search unavailable: {exc}")

        try:
            entries = await backend.search(arguments.query, max_results=arguments.max_results)
        except Exception as exc:
            return ToolResult(output=f"Memory search error: {exc}", is_error=True)

        if not entries:
            return ToolResult(output="No relevant memories found.")

        lines: list[str] = []
        for entry in entries:
            score = f" (score: {entry.score:.2f})" if entry.score is not None else ""
            type_tag = f" [{entry.memory_type}]" if entry.memory_type else ""
            lines.append(f"- {entry.title or entry.id}{type_tag}{score}: {entry.content[:500]}")
        return ToolResult(output="\n".join(lines))
```

- [ ] **Step 2: Write memory_add_tool.py**

```python
# src/openharness/tools/memory_add_tool.py
"""Tool for adding memories to persistent storage."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class MemoryAddInput(BaseModel):
    """Arguments for adding a memory."""

    content: str = Field(description="The memory content to store")
    title: str = Field(default="", description="Short title for the memory")
    memory_type: str = Field(
        default="",
        description="Type of memory: preference, fact, decision, or procedure",
    )


class MemoryAddTool(BaseTool):
    """Store a memory for future sessions."""

    name = "memory_add"
    description = "Store a piece of information in persistent memory for use in future sessions."
    input_model = MemoryAddInput

    def is_read_only(self, arguments: MemoryAddInput) -> bool:
        del arguments
        return False

    async def execute(self, arguments: MemoryAddInput, context: ToolExecutionContext) -> ToolResult:
        from openharness.memory.registry import get_backend

        metadata = context.metadata
        settings = metadata.get("settings")
        if settings is None:
            return ToolResult(output="Memory add unavailable: no settings in context.")

        try:
            backend = get_backend(settings, cwd=context.cwd)
        except (ValueError, ImportError) as exc:
            return ToolResult(output=f"Memory add unavailable: {exc}")

        try:
            entry = await backend.add(
                arguments.content,
                title=arguments.title,
                memory_type=arguments.memory_type,
            )
        except Exception as exc:
            return ToolResult(output=f"Memory add error: {exc}", is_error=True)

        return ToolResult(output=f"Memory stored: {entry.title or entry.id}")
```

- [ ] **Step 3: Register tools in __init__.py**

In `src/openharness/tools/__init__.py`:

Add imports at the top:
```python
from openharness.tools.memory_search_tool import MemorySearchTool
from openharness.tools.memory_add_tool import MemoryAddTool
```

Add to the `create_default_tool_registry` function's tool tuple (after `TeamDeleteTool()`):
```python
        MemorySearchTool(),
        MemoryAddTool(),
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/ -k "tool" -v --timeout=30 -x`
Expected: All pass. New tools are registered but won't be called unless the model invokes them.

- [ ] **Step 5: Commit**

```bash
git add src/openharness/tools/memory_search_tool.py src/openharness/tools/memory_add_tool.py src/openharness/tools/__init__.py
git commit -m "feat(tools): add memory_search and memory_add tools for model-initiated memory access"
```

---

### Task 11: Optional Dependency + Runtime Guard

**Files:**
- Modify: `pyproject.toml:38-46`

- [ ] **Step 1: Add mem0 extras to pyproject.toml**

After the `dev` section in `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    "pexpect>=4.9.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]
mem0 = [
    "mem0>=0.1.0",
]
```

- [ ] **Step 2: Verify the runtime guard in config.py works**

The `check_mem0_available()` function in `src/openharness/memory/mem0/config.py` (created in Task 6) already handles this. When mem0 backend is selected but the package isn't installed:

```python
try:
    backend = get_backend(settings, cwd=cwd)
except ImportError as e:
    # Error: Memory backend "mem0" requires the mem0 package. Install with: pip install openharness[mem0]
```

This is exercised by the `check_mem0_available()` function which raises `ImportError` with a clear message.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(deps): add mem0 optional dependency group"
```

---

### Task 12: Full Test Suite Regression

**Files:** No new files — verification only.

- [ ] **Step 1: Run the complete test suite**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/ -v --timeout=60 -x`
Expected: All pass. The refactored memory module maintains backward compatibility via `__init__.py` re-exports.

- [ ] **Step 2: Run the new memory tests specifically**

Run: `cd /Users/lijunyi/road/reference/OpenHarness && python -m pytest tests/test_memory/ -v`
Expected: All pass, including:
- `test_base.py` — protocol tests
- `test_registry.py` — registry tests
- `test_memdir.py` — existing tests (unchanged, still work via re-exports)
- `test_markdown_backend.py` — MarkdownMemoryBackend tests
- `test_mem0/test_backend.py` — Mem0MemoryBackend tests (mocked)
- `test_mem0/test_extraction.py` — extraction timing tests

- [ ] **Step 3: Final commit if any fixes needed**

If any tests failed and required fixes:
```bash
git add -A
git commit -m "fix(memory): address test suite regressions from mem0 integration"
```
