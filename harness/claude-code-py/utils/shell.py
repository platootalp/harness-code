"""
Shell utilities - working directory and shell operations.

Migrated from TypeScript shell utilities.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def get_cwd() -> str:
    """Get current working directory."""
    return os.getcwd()


def set_cwd(path: str) -> None:
    """Set current working directory."""
    os.chdir(path)


def expand_path(path: str) -> str:
    """Expand user home and environment variables in path."""
    return os.path.expandvars(os.path.expanduser(path))


def is_absolute(path: str) -> bool:
    """Check if path is absolute."""
    return os.path.isabs(path)
