"""File operations for Claude Code.

Provides file reading, writing, encoding detection, line ending handling,
and path utilities. Corresponds to TypeScript src/utils/file.ts and
src/utils/fileRead.ts.
"""

from __future__ import annotations

import contextlib
import logging
import os
import stat
import sys
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Maximum file read size (0.25 MB)
MAX_OUTPUT_SIZE = 0.25 * 1024 * 1024

# Marker included in file-not-found error messages that contain a cwd note.
FILE_NOT_FOUND_CWD_NOTE = "Note: your current working directory is"


# =============================================================================
# Platform Detection
# =============================================================================


class Platform(StrEnum):
    """Supported platforms."""

    MACOS = "macos"
    WINDOWS = "windows"
    WSL = "wsl"
    LINUX = "linux"
    UNKNOWN = "unknown"


def get_platform() -> Platform:
    """Get the current platform.

    Returns:
        The detected platform.
    """
    p = sys.platform
    if p == "darwin":
        return Platform.MACOS
    if p == "win32":
        # Could be WSL detected via /proc/version, simplified here
        return Platform.WINDOWS
    if p == "linux":
        # Check for WSL via /proc/version
        try:
            with open("/proc/version", encoding="utf-8") as f:
                if "microsoft" in f.read().lower():
                    return Platform.WSL
        except OSError:
            pass
        return Platform.LINUX
    return Platform.UNKNOWN


# =============================================================================
# CWD
# =============================================================================


def get_cwd() -> str:
    """Get the current working directory.

    Returns:
        The current working directory path.
    """
    return os.getcwd()


# =============================================================================
# Path Utilities
# =============================================================================


def expand_path(path: str) -> str:
    """Expand ~ and environment variables in a path.

    Args:
        path: The path to expand.

    Returns:
        The expanded path.
    """
    expanded = os.path.expanduser(os.path.expandvars(path))
    return os.path.normpath(expanded)


def normalize_path_for_comparison(path: str) -> str:
    """Normalize a file path for comparison, handling platform differences.

    On Windows, normalizes path separators and converts to lowercase for
    case-insensitive comparison.

    Args:
        path: The path to normalize.

    Returns:
        The normalized path.
    """
    normalized = os.path.normpath(path)

    if get_platform() == Platform.WINDOWS:
        normalized = normalized.replace("/", "\\").lower()

    return normalized


def paths_equal(path1: str, path2: str) -> bool:
    """Compare two file paths for equality, handling Windows case-insensitivity.

    Args:
        path1: First path.
        path2: Second path.

    Returns:
        True if the paths are equal.
    """
    return normalize_path_for_comparison(path1) == normalize_path_for_comparison(path2)


def get_absolute_and_relative_paths(
    path: str | None,
) -> tuple[str | None, str | None]:
    """Get both absolute and relative versions of a path.

    Args:
        path: The path to resolve. May be None.

    Returns:
        A tuple of (absolute_path, relative_path).
    """
    if path is None:
        return (None, None)

    absolute_path = expand_path(path)
    try:
        relative_path = os.path.relpath(absolute_path, get_cwd())
    except ValueError:
        # Can't compute relative path across drives (Windows)
        relative_path = absolute_path

    return (absolute_path, relative_path)


def get_display_path(file_path: str) -> str:
    """Get the display path for a file.

    Uses relative path if within cwd, tilde notation for home directory,
    otherwise absolute path.

    Args:
        file_path: The file path.

    Returns:
        The display-friendly path.
    """
    _, relative_path = get_absolute_and_relative_paths(file_path)

    # Use relative path if it's not going up directories
    if relative_path and not relative_path.startswith(".."):
        return relative_path

    # Use tilde notation for files in home directory
    home = os.path.expanduser("~")
    sep = os.sep
    if file_path.startswith(home + sep):
        return "~" + file_path[len(home) :]

    return file_path


def find_similar_file(file_path: str) -> str | None:
    """Find files with the same name but different extensions in the same directory.

    Args:
        file_path: The path to the file that doesn't exist.

    Returns:
        The found file with a different extension, or None.
    """
    try:
        dir_path = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]

        files = os.listdir(dir_path)
        for f in files:
            f_base = os.path.splitext(f)[0]
            f_full = os.path.join(dir_path, f)
            if f_base == base_name and f_full != file_path:
                return f

    except OSError:
        # ENOENT or other errors - return None
        pass

    return None


async def suggest_path_under_cwd(requested_path: str) -> str | None:
    """Suggest a corrected path under the current working directory.

    Detects the "dropped repo folder" pattern where the model constructs
    an absolute path missing the repo directory component.

    Args:
        requested_path: The absolute path that was not found.

    Returns:
        The corrected path if found under cwd, None otherwise.
    """
    import asyncio

    cwd = get_cwd()
    cwd_parent = os.path.dirname(cwd)

    # Resolve symlinks in the requested path's parent directory
    resolved_path = requested_path
    try:
        resolved_dir = await asyncio.to_thread(
            os.path.realpath, os.path.dirname(requested_path)
        )
        resolved_path = os.path.join(resolved_dir, os.path.basename(requested_path))
    except OSError:
        pass

    # Only check if the requested path is under cwd's parent but not under cwd
    cwd_parent_prefix = os.sep if cwd_parent == os.sep else cwd_parent + os.sep
    if (
        not resolved_path.startswith(os.sep)
        or resolved_path.startswith(cwd_parent_prefix)
    ):
        # Check if it's under cwd parent but not cwd itself
        if (
            resolved_path.startswith(cwd_parent_prefix)
            and not resolved_path.startswith(cwd + os.sep)
            and resolved_path != cwd
        ):
            rel_from_parent = os.path.relpath(resolved_path, cwd_parent)
            corrected = os.path.join(cwd, rel_from_parent)
            try:
                await asyncio.to_thread(os.stat, corrected)
                return corrected
            except OSError:
                return None
        return None

    # Get the relative path from the parent directory
    try:
        rel_from_parent = os.path.relpath(resolved_path, cwd_parent)
    except ValueError:
        return None

    # Check if the same relative path exists under cwd
    corrected = os.path.join(cwd, rel_from_parent)
    try:
        await asyncio.to_thread(os.stat, corrected)
        return corrected
    except OSError:
        return None


# =============================================================================
# Path Existence
# =============================================================================


async def path_exists(path: str) -> bool:
    """Check if a path exists asynchronously.

    Args:
        path: The path to check.

    Returns:
        True if the path exists.
    """
    import asyncio

    try:
        await asyncio.to_thread(os.stat, path)
        return True
    except OSError:
        return False


def path_exists_sync(path: str) -> bool:
    """Check if a path exists synchronously.

    Args:
        path: The path to check.

    Returns:
        True if the path exists.
    """
    try:
        os.stat(path)
        return True
    except OSError:
        return False


# =============================================================================
# Encoding Detection
# =============================================================================


class LineEndingType(StrEnum):
    """Line ending type."""

    CRLF = "CRLF"
    LF = "LF"


def detect_encoding_for_resolved_path(resolved_path: str) -> str:
    """Detect the encoding of a file from its first bytes.

    Checks for BOM markers (UTF-16 LE, UTF-8) and defaults to UTF-8.

    Args:
        resolved_path: The resolved file path.

    Returns:
        The detected encoding name ('utf-8', 'utf-16-le').
    """
    try:
        with open(resolved_path, "rb") as f:
            head = f.read(4096)

        if len(head) == 0:
            return "utf-8"

        if len(head) >= 2 and head[0] == 0xFF and head[1] == 0xFE:
            return "utf-16-le"

        if len(head) >= 3 and head[0] == 0xEF and head[1] == 0xBB and head[2] == 0xBF:
            return "utf-8"

        return "utf-8"
    except OSError:
        return "utf-8"


def detect_file_encoding(file_path: str) -> str:
    """Detect the encoding of a file.

    Args:
        file_path: The file path.

    Returns:
        The detected encoding name.
    """
    resolved = _resolve_symlink_path(file_path)
    if resolved is None:
        return "utf-8"

    try:
        return detect_encoding_for_resolved_path(resolved)
    except OSError:
        logger.debug(f"detectFileEncoding failed: {file_path}")
        return "utf-8"


# =============================================================================
# Line Ending Detection
# =============================================================================


def detect_line_endings_for_string(content: str) -> LineEndingType:
    """Detect line ending type from string content.

    Args:
        content: The file content string.

    Returns:
        The detected line ending type.
    """
    crlf_count = 0
    lf_count = 0

    for i, char in enumerate(content):
        if char == "\n":
            if i > 0 and content[i - 1] == "\r":
                crlf_count += 1
            else:
                lf_count += 1

    return LineEndingType.CRLF if crlf_count > lf_count else LineEndingType.LF


def detect_line_endings(file_path: str, encoding: str = "utf-8") -> LineEndingType:
    """Detect line ending type of a file.

    Args:
        file_path: The file path.
        encoding: The file encoding.

    Returns:
        The detected line ending type.
    """
    try:
        with open(file_path, encoding=encoding, newline="") as f:
            head = f.read(4096)
        return detect_line_endings_for_string(head)
    except OSError:
        return LineEndingType.LF


# =============================================================================
# File Read with Metadata
# =============================================================================


@dataclass
class FileReadMetadata:
    """Metadata returned by read_file_sync_with_metadata."""

    content: str
    encoding: str
    line_endings: LineEndingType


def _resolve_symlink_path(file_path: str) -> str | None:
    """Resolve symlink to target path.

    Args:
        file_path: The file path to resolve.

    Returns:
        The resolved path, or None if the file doesn't exist.
    """
    try:
        if os.path.islink(file_path):
            target = os.readlink(file_path)
            if os.path.isabs(target):
                return target
            return os.path.normpath(os.path.join(os.path.dirname(file_path), target))
        return file_path
    except OSError:
        return None


def read_file_sync_with_metadata(file_path: str) -> FileReadMetadata:
    """Read file content with detected encoding and line endings.

    Performs encoding detection and line ending detection in a single pass,
    then returns the content with CRLF normalized to LF.

    Args:
        file_path: The file path.

    Returns:
        FileReadMetadata with content, encoding, and line_endings.

    Raises:
        OSError: If the file cannot be read.
    """
    resolved = _resolve_symlink_path(file_path)
    if resolved is None:
        raise FileNotFoundError(f"File not found: {file_path}")

    if os.path.islink(file_path):
        logger.debug(f"Reading through symlink: {file_path} -> {resolved}")

    encoding = detect_encoding_for_resolved_path(resolved)
    # Use newline="" to prevent Python's universal newline translation
    # which would convert CRLF to LF before we can detect line endings.
    with open(resolved, encoding=encoding, newline="") as f:
        raw = f.read()

    # Detect line endings from raw head before CRLF normalization
    line_endings = detect_line_endings_for_string(raw[:4096])
    content = raw.replace("\r\n", "\n")

    return FileReadMetadata(
        content=content,
        encoding=encoding,
        line_endings=line_endings,
    )


def read_file_sync(file_path: str) -> str:
    """Read file content synchronously.

    Args:
        file_path: The file path.

    Returns:
        The file content with CRLF normalized to LF.
    """
    return read_file_sync_with_metadata(file_path).content


def read_file_safe(file_path: str) -> str | None:
    """Read file content safely, returning None on error.

    Args:
        file_path: The file path.

    Returns:
        The file content, or None if reading fails.
    """
    try:
        return read_file_sync(file_path)
    except OSError as e:
        logger.error(str(e))
        return None


# =============================================================================
# File Modification Time
# =============================================================================


def get_file_modification_time(file_path: str) -> int:
    """Get the modification time of a file in milliseconds.

    Uses Math.floor semantics (integer seconds) for consistent timestamp
    comparisons across file operations.

    Args:
        file_path: The file path.

    Returns:
        Modification time in seconds (floored).
    """
    return int(os.stat(file_path).st_mtime)


async def get_file_modification_time_async(file_path: str) -> int:
    """Get the modification time of a file asynchronously.

    Uses integer seconds (floored) for consistent comparisons.

    Args:
        file_path: The file path.

    Returns:
        Modification time in seconds (floored).
    """
    import asyncio

    stat_result = await asyncio.to_thread(os.stat, file_path)
    return int(stat_result.st_mtime)


# =============================================================================
# Directory Operations
# =============================================================================


def is_dir_empty(dir_path: str) -> bool:
    """Check if a directory is empty.

    Args:
        dir_path: The directory path.

    Returns:
        True if the directory is empty or does not exist.
    """
    try:
        return len(os.listdir(dir_path)) == 0
    except FileNotFoundError:
        return True
    except PermissionError:
        # macOS protected folders may raise EACCES but dir is not empty
        return False


# =============================================================================
# File Size Validation
# =============================================================================


def is_file_within_read_size_limit(
    file_path: str,
    max_size_bytes: float = MAX_OUTPUT_SIZE,
) -> bool:
    """Check if a file is within the read size limit.

    Args:
        file_path: The file path.
        max_size_bytes: Maximum allowed size in bytes.

    Returns:
        True if the file is within the limit.
    """
    try:
        size = os.stat(file_path).st_size
        return size <= max_size_bytes
    except OSError:
        return False


# =============================================================================
# Content Transformations
# =============================================================================


def convert_leading_tabs_to_spaces(content: str) -> str:
    """Convert leading tabs to spaces in all lines.

    Uses 2 spaces per tab.

    Args:
        content: The content to transform.

    Returns:
        Content with leading tabs replaced by 2 spaces.
    """
    if "\t" not in content:
        return content

    lines = content.splitlines(keepends=True)
    result_lines: list[str] = []
    for line in lines:
        # Count leading tabs
        leading_tabs = 0
        for char in line:
            if char == "\t":
                leading_tabs += 1
            else:
                break

        if leading_tabs > 0:
            result_lines.append("  " * leading_tabs + line[leading_tabs:])
        else:
            result_lines.append(line)

    # Handle case where content doesn't end with newline
    if not content.endswith("\n"):
        result_lines[-1] = result_lines[-1].rstrip("\r")

    return "".join(result_lines)


def add_line_numbers(content: str, start_line: int = 1) -> str:
    """Add line numbers to content.

    Args:
        content: The content to number.
        start_line: The starting line number (1-indexed).

    Returns:
        Content with line number prefixes.
    """
    if not content:
        return ""

    lines = content.splitlines()
    numbered: list[str] = []

    for i, line in enumerate(lines):
        num = i + start_line
        num_str = str(num)
        if len(num_str) >= 6:
            numbered.append(f"{num_str}\u2192{line}")
        else:
            numbered.append(f"{num_str.rjust(6)}\u2192{line}")

    return "\n".join(numbered)


def strip_line_number_prefix(line: str) -> str:
    """Strip line number prefix from a line.

    Handles both `N\u2192` and `N\t` formats.

    Args:
        line: The line with possible prefix.

    Returns:
        The content without the prefix.
    """
    import re

    match = re.match(r"^\s*\d+[\u2192\t](.*)$", line, re.UNICODE)
    return match.group(1) if match else line


# =============================================================================
# File Writing
# =============================================================================


def write_text_content(
    file_path: str,
    content: str,
    encoding: str,
    endings: LineEndingType,
) -> None:
    """Write text content to a file with proper line endings.

    Args:
        file_path: The target file path.
        content: The content to write.
        encoding: The text encoding.
        endings: The line ending type to use.
    """
    to_write = content
    if endings == LineEndingType.CRLF:
        # Normalize existing CRLF to LF first
        normalized = content.replace("\r\n", "\n")
        to_write = "\r\n".join(normalized.split("\n"))

    write_file_sync_and_flush_deprecated(file_path, to_write, encoding=encoding)


def write_file_sync_and_flush_deprecated(
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    mode: int | None = None,
) -> None:
    """Write file content synchronously with flush and optional permission preservation.

    Uses atomic write (temp file + rename) on POSIX. On error falls back to
    direct write. Preserves symlink and file permissions when possible.

    Args:
        file_path: The target file path.
        content: The content to write.
        encoding: The text encoding.
        mode: Optional file permission mode for new files.

    Note:
        Deprecated: Use asyncio.to_thread(os.write) with atomic rename for
        non-blocking writes in new code.
    """
    # Preserve symlink - resolve if target is a symlink
    target_path = file_path
    try:
        link_target = os.readlink(file_path)
        if os.path.isabs(link_target):
            target_path = link_target
        else:
            target_path = os.path.normpath(
                os.path.join(os.path.dirname(file_path), link_target)
            )
        logger.debug(f"Writing through symlink: {file_path} -> {target_path}")
    except OSError:
        # ENOENT (doesn't exist) or EINVAL (not a symlink) - keep original
        pass

    # Get existing file permissions (for preservation)
    target_mode: int | None = None
    try:
        target_mode = stat.S_IMODE(os.stat(target_path).st_mode)
        logger.debug(f"Preserving file permissions: {oct(target_mode)}")
    except FileNotFoundError:
        if mode is not None:
            target_mode = mode
            logger.debug(f"Setting permissions for new file: {oct(target_mode)}")
    except OSError as e:
        raise e

    # Atomic write via temp file
    temp_path = f"{target_path}.tmp.{os.getpid()}.{int(__import__('time').time() * 1000)}"

    try:
        logger.debug(f"Writing to temp file: {temp_path}")

        # Write to temp file
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Apply permissions to temp file if needed
        if target_mode is not None:
            os.chmod(temp_path, target_mode)

        # Atomic rename
        os.replace(temp_path, target_path)
        logger.debug(f"File {target_path} written atomically")

    except OSError:
        # Clean up temp file
        with contextlib.suppress(OSError):
            os.unlink(temp_path)

        # Fallback to direct write
        logger.debug(f"Falling back to non-atomic write for {target_path}")
        with open(target_path, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())


# =============================================================================
# Desktop Path
# =============================================================================


def get_desktop_path() -> str:
    """Get the desktop path for the current platform.

    Returns:
        The desktop directory path.
    """
    platform = get_platform()
    home = os.path.expanduser("~")

    if platform == Platform.MACOS:
        return os.path.join(home, "Desktop")

    if platform == Platform.WINDOWS:
        # For WSL, try to access Windows desktop
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            windows_home = userprofile.replace("\\", "/")
            wsl_path = windows_home.replace(":", "")
            desktop_path = f"/mnt/c{ wsl_path}/Desktop"
            if os.path.exists(desktop_path):
                return desktop_path

        # Fallback: try to find desktop in typical Windows user location
        try:
            users_dir = "/mnt/c/Users"
            for user in os.listdir(users_dir):
                if user in ("Public", "Default", "Default User", "All Users"):
                    continue
                potential = os.path.join(users_dir, user, "Desktop")
                if os.path.exists(potential):
                    return potential
        except OSError:
            pass

    # Linux/unknown: try ~/Desktop
    desktop_path = os.path.join(home, "Desktop")
    if os.path.exists(desktop_path):
        return desktop_path

    # Fallback to home directory
    return home
