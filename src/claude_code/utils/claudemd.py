"""
Claude MD utilities - memory and cache management.

Migrated from TypeScript claudemd utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Cache storage
_file_caches: dict[str, object] = {}


def clear_memory_file_caches() -> None:
    """Clear all in-memory file caches."""
    _file_caches.clear()


def get_cached_value(key: str) -> object | None:
    """Get a cached value."""
    return _file_caches.get(key)


def set_cached_value(key: str, value: object) -> None:
    """Set a cached value."""
    _file_caches[key] = value
