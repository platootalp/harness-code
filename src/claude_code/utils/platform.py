"""
Platform detection for Claude Code.

Provides platform detection (macOS, Windows, WSL, Linux), WSL version detection,
Linux distribution info, and VCS detection.

Migrated from src/utils/platform.ts.
"""

from __future__ import annotations

import os
import re
import sys
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# VCS marker files and their system names
_VCS_MARKERS: list[tuple[str, str]] = [
    (".git", "git"),
    (".hg", "mercurial"),
    (".svn", "svn"),
    (".p4config", "perforce"),
    ("$tf", "tfs"),
    (".tfvc", "tfs"),
    (".jj", "jujutsu"),
    (".sl", "sapling"),
]


class Platform(StrEnum):
    """Supported platforms."""

    MACOS = "macos"
    WINDOWS = "windows"
    WSL = "wsl"
    LINUX = "linux"
    UNKNOWN = "unknown"


SUPPORTED_PLATFORMS: list[Platform] = [Platform.MACOS, Platform.WSL]


@lru_cache(maxsize=1)
def get_platform() -> Platform:
    """
    Detect the current platform.

    Returns:
        The detected platform (macOS, Windows, WSL, Linux, or unknown).
    """
    try:
        p = sys.platform
        if p == "darwin":
            return Platform.MACOS

        if p == "win32":
            return Platform.WINDOWS

        if p == "linux":
            # Check if running in WSL (Windows Subsystem for Linux)
            try:
                proc_version = Path("/proc/version").read_text(encoding="utf-8").lower()
                if "microsoft" in proc_version or "wsl" in proc_version:
                    return Platform.WSL
            except OSError:
                # Error reading /proc/version, assume regular Linux
                pass

            return Platform.LINUX

        return Platform.UNKNOWN
    except Exception:
        return Platform.UNKNOWN


@lru_cache(maxsize=1)
def get_wsl_version() -> str | None:
    """
    Get the WSL version if running on WSL.

    Returns:
        WSL version string ('1', '2', etc.) if running on WSL, None otherwise.
    """
    # Only check for WSL on Linux systems
    if sys.platform != "linux":
        return None

    try:
        proc_version = Path("/proc/version").read_text(encoding="utf-8")

        # First check for explicit WSL version markers (e.g., "WSL2", "WSL3", etc.)
        wsl_version_match = re.search(r"WSL(\d+)", proc_version, re.IGNORECASE)
        if wsl_version_match and wsl_version_match.group(1):
            return wsl_version_match.group(1)

        # If no explicit WSL version but contains Microsoft, assume WSL1
        # This handles the original WSL1 format: "4.4.0-19041-Microsoft"
        if "microsoft" in proc_version.lower():
            return "1"

        # Not WSL or unable to determine version
        return None
    except OSError:
        return None


@lru_cache(maxsize=1)
def get_linux_distro_info() -> dict[str, str] | None:
    """
    Get Linux distribution information from /etc/os-release.

    Returns:
        Dict with linux_distro_id, linux_distro_version, and linux_kernel,
        or None if not on Linux.
    """
    if sys.platform != "linux":
        return None

    result: dict[str, str] = {
        "linux_kernel": os.uname().release,
    }

    try:
        content = Path("/etc/os-release").read_text(encoding="utf-8")
        for line in content.split("\n"):
            match = re.match(r"^(ID|VERSION_ID)=(.*)$", line)
            if match and match.group(1) and match.group(2):
                value = match.group(2).strip('"')
                if match.group(1) == "ID":
                    result["linux_distro_id"] = value
                else:
                    result["linux_distro_version"] = value
    except OSError:
        # /etc/os-release may not exist on all Linux systems
        pass

    return result


async def detect_vcs(dir_path: str | None = None) -> list[str]:
    """
    Detect version control systems present in a directory.

    Checks for VCS marker files/directories (.git, .hg, .svn, etc.) and
    Perforce environment variables.

    Args:
        dir_path: Directory to check. Defaults to current working directory.

    Returns:
        List of detected VCS system names (e.g., ['git', 'perforce']).
    """
    detected: list[str] = []

    # Check for Perforce via env var
    if os.environ.get("P4PORT"):
        detected.append("perforce")

    try:
        target = Path(dir_path) if dir_path else Path.cwd()
        try:
            entries = {e.name for e in target.iterdir()}
        except OSError:
            return detected

        for marker, vcs in _VCS_MARKERS:
            if marker in entries:
                if vcs not in detected:
                    detected.append(vcs)
    except OSError:
        # Directory may not be readable
        pass

    return detected


def detect_vcs_sync(dir_path: str | None = None) -> list[str]:
    """
    Synchronous version of detect_vcs.

    Args:
        dir_path: Directory to check. Defaults to current working directory.

    Returns:
        List of detected VCS system names.
    """
    detected: list[str] = []

    # Check for Perforce via env var
    if os.environ.get("P4PORT"):
        detected.append("perforce")

    try:
        target = Path(dir_path) if dir_path else Path.cwd()
        try:
            entries = {e.name for e in target.iterdir()}
        except OSError:
            return detected

        for marker, vcs in _VCS_MARKERS:
            if marker in entries:
                if vcs not in detected:
                    detected.append(vcs)
    except OSError:
        pass

    return detected
