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
    return cls(settings=settings, cwd=Path(cwd))
