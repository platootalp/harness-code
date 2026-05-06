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