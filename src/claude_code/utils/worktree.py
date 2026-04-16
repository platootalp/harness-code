"""
Worktree utilities - git worktree session management.

Migrated from TypeScript worktree utilities.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Current worktree session state
_current_worktree: dict | None = None


@dataclass
class WorktreeSession:
    """Git worktree session information."""
    path: str
    branch: str | None
    original_cwd: str
    created_at: int
    name: str | None = None


def is_worktree_mode() -> bool:
    """Check if currently in worktree mode."""
    return _current_worktree is not None


def get_current_worktree_session() -> WorktreeSession | None:
    """Get the current worktree session.

    Returns:
        WorktreeSession or None if not in worktree mode
    """
    if _current_worktree is None:
        return None
    return WorktreeSession(**_current_worktree)


def enter_worktree_mode(path: str, branch: str | None = None, original_cwd: str | None = None) -> WorktreeSession:
    """Enter worktree mode by creating/cloning a worktree.

    Args:
        path: Path for the worktree
        branch: Branch name (optional)
        original_cwd: Original working directory

    Returns:
        WorktreeSession with session details
    """
    import time

    # Ensure path exists
    os.makedirs(path, exist_ok=True)

    session = WorktreeSession(
        path=path,
        branch=branch,
        original_cwd=original_cwd or os.getcwd(),
        created_at=int(time.time() * 1000),
        name=os.path.basename(path),
    )

    global _current_worktree
    _current_worktree = {
        "path": session.path,
        "branch": session.branch,
        "original_cwd": session.original_cwd,
        "created_at": session.created_at,
        "name": session.name,
    }

    return session


def exit_worktree_mode() -> str | None:
    """Exit worktree mode.

    Returns:
        Original working directory or None
    """
    global _current_worktree
    if _current_worktree is None:
        return None

    original_cwd = _current_worktree.get("original_cwd")
    _current_worktree = None
    return original_cwd


def get_worktree_path(name: str | None = None) -> str:
    """Get the path for a worktree.

    Args:
        name: Worktree name (optional)

    Returns:
        Path for the worktree directory
    """
    base_dir = os.path.join(tempfile.gettempdir(), "claude-worktrees")
    os.makedirs(base_dir, exist_ok=True)

    if name:
        return os.path.join(base_dir, name)
    return os.path.join(base_dir, f"worktree_{int(os.times().elapsed * 1000)}")


def get_session_id() -> str:
    """Get the current Claude session ID.

    Returns:
        The session ID from environment or a default.
    """
    return os.environ.get("CLAUDE_SESSION_ID", "default")


async def create_worktree_for_session(session_id: str, name: str) -> dict:
    """Create a git worktree for a session.

    Args:
        session_id: The session ID to create a worktree for.
        name: Name/identifier for the worktree.

    Returns:
        Dict with 'worktreePath' and 'worktreeBranch' keys.
    """
    # Find the main git repo (look for .git)
    cwd = os.getcwd()
    git_root = _find_git_root(cwd)

    worktree_dir = os.path.join(tempfile.gettempdir(), "claude-worktrees", name)
    os.makedirs(worktree_dir, exist_ok=True)

    branch_name = f"worktree/{name}"

    # Try to create worktree
    if git_root:
        with contextlib.suppress(subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            subprocess.run(
                ["git", "-C", git_root, "worktree", "add", "-b", branch_name, worktree_dir],
                capture_output=True,
                text=True,
                timeout=30,
            )

    # Record in current state
    enter_worktree_mode(worktree_dir, branch_name, cwd)

    return {
        "worktreePath": worktree_dir,
        "worktreeBranch": branch_name,
    }


async def keep_worktree() -> None:
    """Keep the current worktree (exit without removing)."""
    exit_worktree_mode()


async def cleanup_worktree() -> None:
    """Remove the current worktree and exit worktree mode."""
    session = get_current_worktree_session()
    if session:
        worktree_path = session.path
        exit_worktree_mode()
        # Try to remove the worktree directory
        with contextlib.suppress(OSError):
            if os.path.exists(worktree_path):
                shutil.rmtree(worktree_path)
    else:
        exit_worktree_mode()


async def kill_tmux_session(session_name: str) -> None:
    """Kill a tmux session.

    Args:
        session_name: Name of the tmux session to kill.
    """
    with contextlib.suppress(subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
            timeout=5,
        )


def _find_git_root(path: str) -> str | None:
    """Find the root of a git repository.

    Args:
        path: Starting path to search from.

    Returns:
        Path to git root or None if not found.
    """
    current = path
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None
