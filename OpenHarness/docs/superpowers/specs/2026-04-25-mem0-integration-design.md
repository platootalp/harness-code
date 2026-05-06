# mem0 Integration Design

**Date:** 2026-04-25
**Status:** Draft

## Summary

Integrate [mem0](https://github.com/mem0ai/mem0) as a pluggable memory backend for OpenHarness, alongside the existing Markdown-based memory system. A unified `MemoryBackend` abstraction shields consumers from backend differences, enabling seamless switching via configuration. mem0 brings semantic search (embedding-based retrieval), automatic memory extraction from conversations, user profiles, and graph relationships — a more complete memory layer than the current keyword-based approach.

## Motivation

OpenHarness has a file-based memory system (MEMORY.md + topic markdown files + heuristic keyword search). It works well for human-readable, manually curated memory but has limitations:

- **Keyword search only** — cannot find semantically related memories without exact token overlap
- **Manual curation** — all memories must be written by the user or model explicitly
- **No user profiling** — cannot accumulate user preferences, habits, or personality traits across sessions
- **No relationship graph** — memories are independent files without links

mem0 addresses these gaps while keeping the existing Markdown backend as the default for users who prefer transparency and manual control.

## Architecture

### Approach: Abstract Backend + Dual Implementations

A `MemoryBackend` protocol (ABC) defines the unified interface. Two implementations:
1. **MarkdownMemoryBackend** — wraps the existing memory system (refactored into `memory/markdown/` subpackage)
2. **Mem0MemoryBackend** — wraps the mem0 library (new `memory/mem0/` subpackage)

Consumers (`prompts/context.py`, `engine/query.py`, tools) call through the protocol, unaware of which backend is active.

### File Structure

```
src/openharness/memory/
├── __init__.py              # Compat re-exports + register default backends
├── base.py                  # MemoryBackend, MemoryEntry
├── registry.py              # register_backend(), get_backend()
├── markdown/                # Refactored existing code
│   ├── __init__.py
│   ├── backend.py           # MarkdownMemoryBackend(MemoryBackend)
│   ├── manager.py           # (existing, moved)
│   ├── search.py            # (existing, moved)
│   ├── scan.py              # (existing, moved)
│   ├── memdir.py            # (existing, moved)
│   ├── paths.py             # (existing, moved)
│   └── types.py             # (existing, moved, MemoryHeader kept as internal type)
└── mem0/                    # New
    ├── __init__.py
    ├── backend.py           # Mem0MemoryBackend(MemoryBackend)
    └── config.py            # Client factory + validation

src/openharness/config/settings.py       # MemorySettings + Mem0Settings extensions
src/openharness/prompts/context.py       # Consume via backend
src/openharness/engine/query.py          # Extract hook + compact safety net
src/openharness/tools/memory_search_tool.py  # New: model-initiated memory search
src/openharness/tools/memory_add_tool.py     # New: model-initiated memory add
```

## MemoryBackend Protocol

```python
@dataclass(frozen=True)
class MemoryEntry:
    """Backend-agnostic memory entry."""
    id: str                     # Backend-unique identifier (filename / mem0 memory_id)
    title: str
    content: str
    memory_type: str = ""       # "preference" | "fact" | "decision" | "procedure" | ""
    metadata: dict | None = None
    score: float | None = None  # Search relevance (only set in search results)


class MemoryBackend(ABC):
    """Unified protocol for all memory backends."""

    @abstractmethod
    async def add(self, content: str, *, title: str = "",
                  memory_type: str = "", metadata: dict | None = None) -> MemoryEntry:
        """Add a memory entry."""

    @abstractmethod
    async def search(self, query: str, *, max_results: int = 5) -> list[MemoryEntry]:
        """Search for relevant memories (semantic for mem0, keyword for markdown)."""

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""

    @abstractmethod
    async def list_all(self, *, memory_type: str = "") -> list[MemoryEntry]:
        """List all memories, optionally filtered by type."""

    @abstractmethod
    def load_prompt_section(self, *, max_lines: int = 200) -> str | None:
        """Load memory content for system prompt injection.

        Markdown backend: returns MEMORY.md content.
        mem0 backend: returns cached high-priority memory summary.
        """

    @abstractmethod
    async def extract_and_store(self, messages: list[dict]) -> list[MemoryEntry]:
        """Auto-extract memories from conversation messages.

        Markdown backend: no-op (manual management).
        mem0 backend: calls mem0.add(messages) for automatic extraction.
        """

    def should_extract(self, *, message_count: int, elapsed_seconds: float,
                       extract_every_n_messages: int, extract_every_seconds: float) -> bool:
        """Determine if extraction should run. Dual trigger: count OR time threshold."""
        return (
            message_count >= extract_every_n_messages
            or elapsed_seconds >= extract_every_seconds
        )
```

### Method Synchronicity Design

- `load_prompt_section()` is **synchronous** — it reads from a cache, no network calls. This avoids making `build_runtime_system_prompt()` async.
- `search()` is **async** — may involve network/embedding computation. Results are pre-fetched in the async QueryEngine flow before being passed to prompt construction.
- `extract_and_store()` is **async** — always involves IO (file writes or API calls).

## Backend Registration & Configuration

### Registry

```python
# memory/registry.py
_backends: dict[str, type[MemoryBackend]] = {}

def register_backend(name: str, cls: type[MemoryBackend]) -> None:
    _backends[name] = cls

def get_backend(settings: Settings, *, cwd: str | Path) -> MemoryBackend:
    backend_name = settings.memory.backend
    cls = _backends.get(backend_name)
    if cls is None:
        raise ValueError(f"Unknown memory backend: {backend_name}")
    return cls(settings=settings, cwd=cwd)
```

Default backends are registered at import time:
```python
# memory/__init__.py
register_backend("markdown", MarkdownMemoryBackend)
register_backend("mem0", Mem0MemoryBackend)
```

### Configuration Extension

```python
class Mem0Settings(BaseModel):
    """mem0-specific configuration."""
    storage: str = "local"                    # "local" | "cloud" | "server"
    vector_store: str = "chroma"              # "chroma" | "qdrant"
    embedder: str = "openai"                  # Embedding model provider (requires corresponding API key in environment)
    embedder_model: str = "text-embedding-3-small"  # For openai embedder; other providers may differ
    api_key: str | None = None                # For cloud/server mode
    base_url: str | None = None               # For self-hosted server
    auto_extract: bool = True
    extract_user_id: str = "default"          # mem0 user_id for memory scoping
    extract_every_n_messages: int = 5         # Extract every N user-assistant turns
    extract_every_seconds: float = 300.0      # Or every 5 minutes, whichever comes first

class MemorySettings(BaseModel):
    enabled: bool = True
    backend: str = "markdown"                 # NEW: "markdown" | "mem0"
    max_files: int = 5
    max_entrypoint_lines: int = 200
    mem0: Mem0Settings = Mem0Settings()       # NEW
```

### Switching Mechanisms

| Method | Example |
|--------|---------|
| `settings.json` | `{"memory": {"backend": "mem0"}}` |
| CLI | `oh config set memory.backend mem0` |
| Environment variable | `OH_MEMORY_BACKEND=mem0` |

## MarkdownMemoryBackend

Wraps the existing memory system. Code moves from `memory/*.py` to `memory/markdown/*.py` without behavioral changes.

```python
class MarkdownMemoryBackend(MemoryBackend):
    async def add(self, content, *, title="", memory_type="", metadata=None):
        path = add_memory_entry(self.cwd, title or "memory", content)
        return MemoryEntry(id=path.name, title=title, content=content, memory_type=memory_type)

    async def search(self, query, *, max_results=5):
        headers = find_relevant_memories(query, self.cwd, max_results=max_results)
        return [MemoryEntry(id=h.path.name, title=h.title,
                           content=h.path.read_text(), memory_type=h.memory_type)
                for h in headers]

    async def delete(self, id):
        return remove_memory_entry(self.cwd, Path(id).stem)

    async def list_all(self, *, memory_type=""):
        return [MemoryEntry(id=p.name, title=p.stem, content=p.read_text())
                for p in list_memory_files(self.cwd)]

    def load_prompt_section(self, *, max_lines=200):
        return load_memory_prompt(self.cwd, max_entrypoint_lines=max_lines)

    async def extract_and_store(self, messages):
        return []  # Markdown backend: manual management only
```

### API Compatibility

`memory/__init__.py` re-exports all existing public names so no external code breaks:
```python
from openharness.memory.markdown.manager import add_memory_entry, list_memory_files, remove_memory_entry
from openharness.memory.markdown.search import find_relevant_memories
from openharness.memory.markdown.memdir import load_memory_prompt
from openharness.memory.markdown.paths import get_memory_entrypoint, get_project_memory_dir
```

## Mem0MemoryBackend

### Client Initialization (Lazy)

```python
class Mem0MemoryBackend(MemoryBackend):
    def _get_client(self):
        if self._client is not None:
            return self._client

        mem0_config = self.settings.memory.mem0
        if mem0_config.storage == "local":
            from mem0 import Memory
            config = {
                "vector_store": {
                    "provider": mem0_config.vector_store,
                    "config": {
                        "collection_name": f"oh_{_project_slug(self.cwd)}",
                        "path": str(Path.home() / ".openharness" / "mem0_data"),
                    }
                },
                "embedder": {
                    "provider": mem0_config.embedder,
                    "config": {"model": mem0_config.embedder_model},
                },
            }
            self._client = Memory.from_config(config)
        elif mem0_config.storage in ("cloud", "server"):
            from mem0 import MemoryClient
            self._client = MemoryClient(api_key=mem0_config.api_key, base_url=mem0_config.base_url)
        return self._client
```

### Core Operations

- **add**: Calls `client.add(content, user_id=user_id, metadata={...})`, maps result to `MemoryEntry`
- **search**: Calls `client.search(query, user_id=user_id, limit=max_results)`, includes `score` from mem0
- **delete**: Calls `client.delete(id)`
- **list_all**: Calls `client.get_all(user_id=user_id)`, optional `memory_type` filter on metadata
- **load_prompt_section**: Reads from a local cache file (`~/.openharness/mem0_cache/{project-slug}.md`). Cache is updated by `extract_and_store()`.
- **extract_and_store**: Calls `client.add(messages, user_id=user_id)` for automatic fact/preference extraction, then updates prompt cache with high-priority memories

### Information Layering (Prompt Injection)

mem0 backend uses a **prompt cache** to keep `load_prompt_section()` synchronous:

1. `extract_and_store()` runs → mem0 extracts facts/preferences
2. High-priority memories (type=`preference`, high scores) are formatted into a markdown cache file
3. Cache path: `~/.openharness/mem0_cache/{project-slug}.md`
4. `load_prompt_section()` reads this cache file — pure file I/O, no network

This ensures prompt assembly remains fast and synchronous while mem0's semantic content gets injected.

## Memory Extraction Timing

### Dual-Trigger Strategy

Memory extraction from conversations uses two independent triggers — either one is sufficient:

1. **Message count threshold**: After every N user-assistant turns (default: 5)
2. **Time threshold**: After T seconds since last extraction (default: 300 = 5 min)

Plus a **safety net**:
3. **Before auto-compact**: Extract memories before the context window is compressed, ensuring details are preserved before they're summarized away

### Integration in QueryEngine

```python
class QueryEngine:
    def __init__(self, ...):
        self._last_extract_at: float = time.monotonic()
        self._messages_since_extract: int = 0

    async def _maybe_extract_memories(self, backend, messages):
        """Dual-trigger extraction: message count OR time elapsed."""
        if not self.settings.memory.mem0.auto_extract:
            return
        config = self.settings.memory.mem0
        elapsed = time.monotonic() - self._last_extract_at
        if backend.should_extract(
            message_count=self._messages_since_extract,
            elapsed_seconds=elapsed,
            extract_every_n_messages=config.extract_every_n_messages,
            extract_every_seconds=config.extract_every_seconds,
        ):
            await backend.extract_and_store(messages)
            self._last_extract_at = time.monotonic()
            self._messages_since_extract = 0

    async def _before_compact(self, messages, backend):
        """Safety net: extract before compact to avoid losing details."""
        if self.settings.memory.mem0.auto_extract:
            await backend.extract_and_store(messages)
            self._last_extract_at = time.monotonic()
            self._messages_since_extract = 0
```

Extraction accumulates messages from the last extraction point, so mem0 sees the full conversation context, not just the latest turn.

Note: `extract_and_store()` returns `[]` for the Markdown backend (no-op), so `isinstance` checks are not needed in QueryEngine. The `auto_extract` setting in `Mem0Settings` controls whether extraction runs; for the markdown backend, this setting is irrelevant since the method is a no-op.

## Query Loop Integration

### prompts/context.py

The `build_runtime_system_prompt()` function is modified to go through the backend:

```python
# Before (simplified)
if settings.memory.enabled:
    memory_section = load_memory_prompt(cwd, ...)
    relevant = find_relevant_memories(latest_user_prompt, cwd, ...)

# After
if settings.memory.enabled:
    backend = get_backend(settings, cwd=cwd)
    memory_section = backend.load_prompt_section(
        max_lines=settings.memory.max_entrypoint_lines,
    )
    if memory_section:
        sections.append(memory_section)

    # search() is async — pre-fetched in QueryEngine before prompt construction
    if relevant_memories:  # passed in from QueryEngine
        lines = ["# Relevant Memories"]
        for entry in relevant_memories:
            lines.extend(["", f"## {entry.title or entry.id}",
                        "```md", entry.content[:8000], "```"])
        sections.append("\n".join(lines))
```

Since `search()` is async and `build_runtime_system_prompt()` is sync, the search is performed in `QueryEngine.submit_message()` before calling prompt construction. The results are passed as a parameter.

### Memory Tools

Two new tools for model-initiated memory operations (only registered when mem0 backend is active):

```python
class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "Search persistent memory for relevant context"
    # Input: query (str), max_results (int, default 5)

class MemoryAddTool(BaseTool):
    name = "memory_add"
    description = "Store a memory for future sessions"
    # Input: content (str), title (str), memory_type (str, optional)
```

These tools are registered for both backends. For markdown backend, `memory_search` delegates to the keyword-based `find_relevant_memories()`, and `memory_add` creates a new MEMORY.md topic file. This gives the model a uniform way to interact with memory regardless of backend.

## Data Flow

```
User message → QueryEngine.submit_message()
               │
               ├─ 1. Pre-fetch relevant memories (async)
               │     backend.search(latest_user_prompt)
               │       markdown: keyword match on MEMORY.md files
               │       mem0: embedding-based semantic search
               │
               ├─ 2. build_runtime_system_prompt(relevant_memories=...)
               │     ├─ backend.load_prompt_section()  [sync, cache]
               │     │     markdown: reads MEMORY.md
               │     │     mem0: reads prompt cache file
               │     │
               │     └─ Appends relevant_memories as "# Relevant Memories" section
               │
               ├─ 3. Query loop (LLM calls + tool execution)
               │     └─ Model can call memory_search / memory_add tools
               │
               ├─ 4. After each assistant response
               │     └─ _maybe_extract_memories() — dual-trigger check
               │           (message count OR time threshold)
               │
               └─ 5. Before auto-compact
                     └─ _before_compact() — safety net extraction
```

## Dependency Management

- `mem0` is an **optional dependency** — only required when `memory.backend = "mem0"`
- `pyproject.toml` adds a new extras group: `pip install openharness[mem0]`
- Runtime guard: if mem0 backend is configured but `mem0` is not installed, emit a clear error:
  ```
  Memory backend "mem0" requires the mem0 package. Install with: pip install openharness[mem0]
  ```
- `mem0`'s own dependencies (chromadb, openai embeddings, etc.) are pulled in via the extras group

## Testing Strategy

| Test File | Scope |
|-----------|-------|
| `test_memory/test_base.py` | Protocol compliance — all backends satisfy MemoryBackend |
| `test_memory/test_mem0/test_backend.py` | Mem0MemoryBackend with mocked mem0 client |
| `test_memory/test_mem0/test_extraction.py` | Extraction timing (dual-trigger, safety net) |
| `test_memory/test_registry.py` | Backend registration, switching, error cases |
| `test_memory/test_markdown_backend.py` | MarkdownMemoryBackend via protocol |
| Existing `test_memory/test_memdir.py` | Unchanged — tests still pass via compat re-exports |
| `test_integration/test_memory_query_loop.py` | End-to-end: search results in prompt, extraction hook |

## Out of Scope

- Memory migration tool (MEMORY.md → mem0) — can be added later as a CLI command
- Memory sync across devices — mem0 cloud handles this, but no custom sync logic
- Memory UI in TUI — future enhancement
- Memory analytics/usage tracking — future enhancement
- ohmo (agent mode) integration — follows same backend pattern, separate task
