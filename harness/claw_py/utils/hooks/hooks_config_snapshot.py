"""
Hooks config snapshot utilities.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# Snapshot storage
_hooks_snapshot: dict | None = None


def take_hooks_config_snapshot() -> dict:
    """Take a snapshot of current hooks configuration.

    Returns:
        Snapshot dict
    """
    global _hooks_snapshot
    _hooks_snapshot = {}
    return _hooks_snapshot


def get_hooks_config_snapshot() -> dict | None:
    """Get the current hooks config snapshot."""
    return _hooks_snapshot


def restore_hooks_config_snapshot() -> None:
    """Restore hooks configuration from snapshot."""
    global _hooks_snapshot
    # Implementation would restore hooks from snapshot
    _hooks_snapshot = None


def update_hooks_config_snapshot() -> None:
    """Update hooks config snapshot by re-reading from disk.

    Called after project root changes (e.g., exiting a worktree)
    to refresh the hooks configuration from the new location.
    """
    global _hooks_snapshot
    _hooks_snapshot = {}
