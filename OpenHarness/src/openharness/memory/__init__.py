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