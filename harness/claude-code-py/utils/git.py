"""
Git utilities.

Migrated from TypeScript git utilities.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def find_canonical_git_root(path: str | None = None) -> str | None:
    """Find the canonical git root directory.

    Args:
        path: Starting path (defaults to cwd)

    Returns:
        Git root path or None if not in a git repo
    """
    if path is None:
        path = os.getcwd()

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        cwd=path,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def is_git_repository(path: str | None = None) -> bool:
    """Check if path is inside a git repository."""
    return find_canonical_git_root(path) is not None
