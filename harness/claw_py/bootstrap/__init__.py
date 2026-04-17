"""
Bootstrap module - application initialization state.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Application state
_original_cwd: str | None = None
_app_initialized: bool = False
_project_root: str | None = None


def set_original_cwd(path: str) -> None:
    """Set the original working directory."""
    global _original_cwd
    _original_cwd = path


def get_original_cwd() -> str | None:
    """Get the original working directory."""
    return _original_cwd


def is_app_initialized() -> bool:
    """Check if app is initialized."""
    return _app_initialized


def set_app_initialized(value: bool = True) -> None:
    """Set app initialization state."""
    global _app_initialized
    _app_initialized = value


def set_project_root(path: str) -> None:
    """Set the project root directory."""
    global _project_root
    _project_root = path


def get_project_root() -> str:
    """Get the project root directory.

    Walks up from current directory looking for a git repo (.git directory)
    or uses the stored project root, or falls back to current directory.

    Returns:
        The project root directory path.
    """
    global _project_root

    if _project_root:
        return _project_root

    # Walk up from current directory looking for .git
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").is_dir():
            return str(parent)

    # Fall back to current directory
    return str(cwd)
