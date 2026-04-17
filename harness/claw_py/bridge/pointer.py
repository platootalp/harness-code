"""Bridge pointer file management for crash-recovery.

Written immediately after a bridge session is created, periodically
refreshed during the session, and cleared on clean shutdown. If the
process dies unclean (crash, kill -9, terminal closed), the pointer
persists. On next startup, Remote Control detects it and offers
to resume via the --session-id flow.

Staleness is checked against the file's mtime (not an embedded timestamp)
so that a periodic re-write with the same content serves as a refresh —
matches the backend's rolling 4h TTL semantics.

TypeScript equivalent: src/bridge/bridgePointer.ts
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

# =============================================================================
# Constants
# =============================================================================

BRIDGE_POINTER_TTL_MS = 4 * 60 * 60 * 1000

# =============================================================================
# Testing helpers (not part of public API)
# =============================================================================

_projects_dir_override: str | None = None


def _override_projects_dir(path: str) -> None:
    """Override the projects directory for testing."""
    global _projects_dir_override
    _projects_dir_override = path


def _restore_projects_dir(original: str | None) -> None:
    """Restore the projects directory after testing."""
    global _projects_dir_override
    _projects_dir_override = original


# =============================================================================
# Types
# =============================================================================


class BridgePointerSource(StrEnum):
    """Source of the bridge session."""

    STANDALONE = "standalone"
    REPL = "repl"


@dataclass
class BridgePointer:
    """Crash-recovery pointer for Remote Control sessions.

    Attributes:
        session_id: Unique session identifier.
        environment_id: Client-generated UUID for idempotent environment registration.
        source: Whether the bridge was launched standalone or from the REPL.
    """

    session_id: str
    environment_id: str
    source: str


@dataclass
class BridgePointerWithAge(BridgePointer):
    """BridgePointer extended with age information."""

    age_ms: float = 0.0


# =============================================================================
# Internal helpers
# =============================================================================


def _safe_json_parse(raw: str) -> dict[str, object] | None:
    """Parse JSON safely, returning None on failure."""
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        return None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _log_for_debugging(msg: str) -> None:
    """Debug logging stub. In production, would call the real log utility."""
    pass


def _time_ms() -> float:
    """Return current time in milliseconds."""
    return time.time() * 1000


# =============================================================================
# Path Resolution
# =============================================================================


def _get_projects_dir() -> str:
    """Return the projects directory path."""
    if _projects_dir_override is not None:
        return _projects_dir_override
    xdg_data_home = os.environ.get("XDG_DATA_HOME", "")
    if xdg_data_home:
        return os.path.join(xdg_data_home, "claude")
    return os.path.expanduser("~/.local/share/claude")


def _sanitize_path(path: str) -> str:
    """Normalize a path for use in a relative filename component.

    Takes a potentially-absolute path and returns a safe relative path.
    E.g. '/home/user/project' -> 'home/user/project'
    """
    # Normalize to forward slashes
    normalized = path.replace("\\", "/")

    # Strip leading separator for absolute paths
    if normalized.startswith("/"):
        normalized = normalized[1:]

    # Split and sanitize each component
    parts = []
    for p in normalized.split("/"):
        clean = "".join(c if c.isalnum() or c in "_-." else "_" for c in p)
        if clean:
            parts.append(clean)

    return "/".join(parts) if parts else "root"


def get_bridge_pointer_path(dir: str) -> str:
    """Get the path to the bridge pointer file for a given directory."""
    projects_dir = _get_projects_dir()
    sanitized = _sanitize_path(dir)
    return os.path.join(projects_dir, sanitized, "bridge-pointer.json")


# =============================================================================
# Internal read implementation
# =============================================================================


async def _read_bridge_pointer_impl(
    dir: str,
) -> BridgePointerWithAge | None:
    """Internal read that returns BridgePointerWithAge."""
    path = get_bridge_pointer_path(dir)
    mtime_ms: float
    raw: str
    try:
        stat_result = os.stat(path)
        mtime_ms = stat_result.st_mtime * 1000
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except OSError:
        return None

    parsed = _safe_json_parse(raw)
    if parsed is None:
        _log_for_debugging(f"[bridge:pointer] invalid JSON, clearing: {path}")
        await _clear_pointer_path(path)
        return None

    if (
        not isinstance(parsed.get("sessionId"), str)
        or not isinstance(parsed.get("environmentId"), str)
        or not isinstance(parsed.get("source"), str)
    ):
        _log_for_debugging(
            f"[bridge:pointer] invalid schema, clearing: {path}"
        )
        await _clear_pointer_path(path)
        return None

    # Cast after isinstance checks to satisfy mypy
    session_id_val = cast(str, parsed["sessionId"])
    env_id_val = cast(str, parsed["environmentId"])
    source_val = cast(str, parsed["source"])

    if source_val not in ("standalone", "repl"):
        _log_for_debugging(
            f"[bridge:pointer] invalid source value '{source_val}', clearing: {path}"
        )
        await _clear_pointer_path(path)
        return None

    age_ms = max(0.0, _time_ms_impl() - mtime_ms)
    if age_ms > BRIDGE_POINTER_TTL_MS:
        _log_for_debugging(
            f"[bridge:pointer] stale (>4h mtime), clearing: {path}"
        )
        await _clear_pointer_path(path)
        return None

    return BridgePointerWithAge(
        session_id=session_id_val,
        environment_id=env_id_val,
        source=source_val,
        age_ms=age_ms,
    )


async def _clear_pointer_path(path: str) -> None:
    """Clear a pointer file at a specific path (internal helper)."""
    try:
        os.unlink(path)
    except OSError as err:
        if err.errno != 2:  # ENOENT
            _log_for_debugging(f"[bridge:pointer] clear failed: {err}")


# =============================================================================
# Write
# =============================================================================


async def write_bridge_pointer(dir: str, pointer: BridgePointer) -> None:
    """Write the crash-recovery pointer.

    Also used to refresh mtime during long sessions. Best-effort —
    logs and swallows on error.
    """
    path = get_bridge_pointer_path(dir)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "sessionId": pointer.session_id,
            "environmentId": pointer.environment_id,
            "source": str(pointer.source),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        _log_for_debugging(f"[bridge:pointer] wrote {path}")
    except OSError as err:
        _log_for_debugging(f"[bridge:pointer] write failed: {err}")


# =============================================================================
# Read
# =============================================================================


async def read_bridge_pointer(
    dir: str,
) -> BridgePointerWithAge | None:
    """Read the bridge pointer and its age.

    Returns None on any failure: missing file, corrupted JSON, schema mismatch,
    or stale (mtime > 4h ago). Stale/invalid pointers are deleted.
    """
    return await _read_bridge_pointer_impl(dir)


# =============================================================================
# Clear
# =============================================================================


async def clear_bridge_pointer(dir: str) -> None:
    """Delete the bridge pointer file.

    Idempotent — ENOENT is expected when the process shut down clean.
    """
    path = get_bridge_pointer_path(dir)
    try:
        os.unlink(path)
        _log_for_debugging(f"[bridge:pointer] cleared {path}")
    except OSError as err:
        if err.errno != 2:  # ENOENT
            _log_for_debugging(f"[bridge:pointer] clear failed: {err}")


# =============================================================================
# Worktree-aware read
# =============================================================================


async def _get_worktree_paths(dir: str) -> list[str]:
    """Get git worktree paths for a directory.

    Returns an empty list on any error (not a git repo, git not installed).
    """
    import asyncio

    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "worktree", "list", "--porcelain",
            cwd=dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
        if proc.returncode != 0:
            return []
        paths = []
        for line in stdout.decode("utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith(" "):
                if not stripped.startswith("HEAD "):
                    path = stripped.rstrip("/")
                    if path and os.path.isabs(path):
                        paths.append(path)
        return paths
    except (TimeoutError, OSError, ValueError):
        return []


async def read_bridge_pointer_across_worktrees(
    dir: str,
) -> tuple[BridgePointerWithAge, str] | None:
    """Worktree-aware read for --continue.

    The REPL bridge writes its pointer to getOriginalCwd() which may be
    mutated to a worktree path — but `claude remote-control --continue`
    runs with shell CWD. This fans out across git worktree siblings to
    find the freshest pointer.

    Fast path: checks `dir` first. Only shells out to git worktree list
    if that misses.

    Args:
        dir: Current working directory path.

    Returns:
        A tuple of (pointer, found_dir) if found, else None.
    """
    # Fast path: current dir
    ptr = await _read_bridge_pointer_impl(dir)
    if ptr is not None:
        return (ptr, dir)

    # Fanout: scan worktree siblings
    worktrees = await _get_worktree_paths(dir)
    if len(worktrees) <= 1:
        return None

    # Cap fanout at 50
    if len(worktrees) > 50:
        _log_for_debugging(
            f"[bridge:pointer] {len(worktrees)} worktrees exceeds fanout cap 50, skipping"
        )
        return None

    # Dedupe against dir
    dir_key = _sanitize_path(dir)
    candidates = [
        wt for wt in worktrees if _sanitize_path(wt) != dir_key
    ]

    # Parallel stat+read
    async def try_read(wt: str) -> tuple[BridgePointerWithAge, str] | None:
        p = await _read_bridge_pointer_impl(wt)
        return (p, wt) if p else None

    import asyncio

    results = await asyncio.gather(
        *[try_read(wt) for wt in candidates]
    )

    # Pick freshest (lowest ageMs)
    freshest: tuple[BridgePointerWithAge, str] | None = None
    for r in results:
        if r is not None:
            ptr_item, wt_dir = r
            if freshest is None or ptr_item.age_ms < freshest[0].age_ms:
                freshest = (ptr_item, wt_dir)

    if freshest:
        _log_for_debugging(
            f"[bridge:pointer] fanout found pointer in worktree {freshest[1]} "
            f"(ageMs={freshest[0].age_ms})"
        )

    return freshest


# =============================================================================
# Time dependency (overrideable for testing)
# =============================================================================


def _time_ms_impl() -> float:
    return time.time() * 1000


def _set_time_ms(fn: Callable[[], float]) -> None:
    """Override time_ms for testing."""
    global _time_ms_impl
    _time_ms_impl = fn
