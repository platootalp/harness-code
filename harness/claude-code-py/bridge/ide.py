"""IDE detection for bridge connections.

Detects IDEs that have a running Claude Code extension/plugin by:
- Reading lockfiles from ~/.claude/ide/ directory
- Checking process running status
- Validating workspace folder matching

Supports VS Code family (VS Code, Cursor, Windsurf) and JetBrains IDEs.

TypeScript equivalent: src/utils/ide.ts
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# IDE Type Enum
# =============================================================================


class IdeType(StrEnum):
    """Supported IDE types."""

    CURSOR = "cursor"
    WINDSURF = "windsurf"
    VSCODE = "vscode"
    PYCHARM = "pycharm"
    INTELLIJ = "intellij"
    WEBSTORM = "webstorm"
    PHPSTORM = "phpstorm"
    RUBYMINE = "rubymine"
    CLION = "clion"
    GOLAND = "goland"
    RIDER = "rider"
    DATAGRIP = "datagrip"
    APPCODE = "appcode"
    DATASPELL = "dataspell"
    AQUA = "aqua"
    GATEWAY = "gateway"
    FLEET = "fleet"
    ANDROIDSTUDIO = "androidstudio"


# =============================================================================
# IDE Configuration
# =============================================================================


class IdeKind(StrEnum):
    """IDE kind classification."""

    VSCODE = "vscode"
    JETBRAINS = "jetbrains"


@dataclass
class IdeConfig:
    """Configuration for an IDE type."""

    ide_kind: IdeKind
    display_name: str
    process_keywords_mac: list[str]
    process_keywords_windows: list[str]
    process_keywords_linux: list[str]


# IDE configurations mapped by IdeType
SUPPORTED_IDE_CONFIGS: dict[IdeType, IdeConfig] = {
    IdeType.CURSOR: IdeConfig(
        ide_kind=IdeKind.VSCODE,
        display_name="Cursor",
        process_keywords_mac=["Cursor Helper", "Cursor.app"],
        process_keywords_windows=["cursor.exe"],
        process_keywords_linux=["cursor"],
    ),
    IdeType.WINDSURF: IdeConfig(
        ide_kind=IdeKind.VSCODE,
        display_name="Windsurf",
        process_keywords_mac=["Windsurf Helper", "Windsurf.app"],
        process_keywords_windows=["windsurf.exe"],
        process_keywords_linux=["windsurf"],
    ),
    IdeType.VSCODE: IdeConfig(
        ide_kind=IdeKind.VSCODE,
        display_name="VS Code",
        process_keywords_mac=["Visual Studio Code", "Code Helper"],
        process_keywords_windows=["code.exe"],
        process_keywords_linux=["code"],
    ),
    IdeType.INTELLIJ: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="IntelliJ IDEA",
        process_keywords_mac=["IntelliJ IDEA"],
        process_keywords_windows=["idea64.exe"],
        process_keywords_linux=["idea", "intellij"],
    ),
    IdeType.PYCHARM: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="PyCharm",
        process_keywords_mac=["PyCharm"],
        process_keywords_windows=["pycharm64.exe"],
        process_keywords_linux=["pycharm"],
    ),
    IdeType.WEBSTORM: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="WebStorm",
        process_keywords_mac=["WebStorm"],
        process_keywords_windows=["webstorm64.exe"],
        process_keywords_linux=["webstorm"],
    ),
    IdeType.PHPSTORM: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="PhpStorm",
        process_keywords_mac=["PhpStorm"],
        process_keywords_windows=["phpstorm64.exe"],
        process_keywords_linux=["phpstorm"],
    ),
    IdeType.RUBYMINE: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="RubyMine",
        process_keywords_mac=["RubyMine"],
        process_keywords_windows=["rubymine64.exe"],
        process_keywords_linux=["rubymine"],
    ),
    IdeType.CLION: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="CLion",
        process_keywords_mac=["CLion"],
        process_keywords_windows=["clion64.exe"],
        process_keywords_linux=["clion"],
    ),
    IdeType.GOLAND: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="GoLand",
        process_keywords_mac=["GoLand"],
        process_keywords_windows=["goland64.exe"],
        process_keywords_linux=["goland"],
    ),
    IdeType.RIDER: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="Rider",
        process_keywords_mac=["Rider"],
        process_keywords_windows=["rider64.exe"],
        process_keywords_linux=["rider"],
    ),
    IdeType.DATAGRIP: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="DataGrip",
        process_keywords_mac=["DataGrip"],
        process_keywords_windows=["datagrip64.exe"],
        process_keywords_linux=["datagrip"],
    ),
    IdeType.APPCODE: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="AppCode",
        process_keywords_mac=["AppCode"],
        process_keywords_windows=["appcode.exe"],
        process_keywords_linux=["appcode"],
    ),
    IdeType.DATASPELL: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="DataSpell",
        process_keywords_mac=["DataSpell"],
        process_keywords_windows=["dataspell64.exe"],
        process_keywords_linux=["dataspell"],
    ),
    IdeType.AQUA: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="Aqua",
        process_keywords_mac=[],
        process_keywords_windows=["aqua64.exe"],
        process_keywords_linux=[],
    ),
    IdeType.GATEWAY: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="Gateway",
        process_keywords_mac=[],
        process_keywords_windows=["gateway64.exe"],
        process_keywords_linux=[],
    ),
    IdeType.FLEET: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="Fleet",
        process_keywords_mac=[],
        process_keywords_windows=["fleet.exe"],
        process_keywords_linux=[],
    ),
    IdeType.ANDROIDSTUDIO: IdeConfig(
        ide_kind=IdeKind.JETBRAINS,
        display_name="Android Studio",
        process_keywords_mac=["Android Studio"],
        process_keywords_windows=["studio64.exe"],
        process_keywords_linux=["android-studio"],
    ),
}


# =============================================================================
# IDE Info
# =============================================================================


@dataclass
class DetectedIDEInfo:
    """Information about a detected IDE.

    Attributes:
        name: Display name of the IDE.
        port: TCP port number for the extension connection.
        workspace_folders: List of workspace folders the IDE has open.
        url: Full URL to connect to the IDE extension.
        is_valid: Whether the IDE workspace matches our current working directory.
        auth_token: Optional auth token for the connection.
        ide_running_in_windows: Whether the IDE is running in Windows (WSL context).
    """

    name: str
    port: int
    workspace_folders: list[str]
    url: str
    is_valid: bool
    auth_token: str | None = None
    ide_running_in_windows: bool | None = None


@dataclass
class IdeLockfileInfo:
    """Information parsed from an IDE lockfile.

    Attributes:
        workspace_folders: List of workspace folders.
        port: TCP port number.
        pid: Process ID of the IDE (if available).
        ide_name: Name of the IDE from the lockfile.
        use_web_socket: Whether to use WebSocket transport.
        running_in_windows: Whether IDE is running in Windows.
        auth_token: Auth token from the lockfile.
    """

    workspace_folders: list[str]
    port: int
    pid: int | None = None
    ide_name: str | None = None
    use_web_socket: bool = False
    running_in_windows: bool = False
    auth_token: str | None = None


# =============================================================================
# Platform Detection
# =============================================================================


def get_platform() -> str:
    """Get the current platform.

    Returns:
        'macos', 'windows', 'linux', or 'wsl'.
    """
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    # Check for WSL
    if os.path.exists("/proc/version"):
        try:
            version = Path("/proc/version").read_text().lower()
            if "microsoft" in version or "wsl" in version:
                return "wsl"
        except OSError:
            pass
    return "linux"


# =============================================================================
# IDE Lockfile Paths
# =============================================================================


def get_claude_config_home() -> Path:
    """Get the Claude config home directory.

    Returns:
        Path to ~/.claude or equivalent.
    """
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "claude"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "claude"
    # Linux and others
    return Path.home() / ".claude"


def get_ide_lockfile_dir() -> Path:
    """Get the directory containing IDE lockfiles.

    Returns:
        Path to the IDE lockfile directory.
    """
    return get_claude_config_home() / "ide"


def get_ide_lockfile_paths() -> list[Path]:
    """Get all potential IDE lockfile directories.

    For WSL, also includes Windows-side paths.

    Returns:
        List of directories to search for lockfiles.
    """
    paths: list[Path] = [get_ide_lockfile_dir()]
    return paths


# =============================================================================
# Lockfile Reading
# =============================================================================


def read_ide_lockfile(path: Path) -> IdeLockfileInfo | None:
    """Read and parse an IDE lockfile.

    Args:
        path: Path to the lockfile.

    Returns:
        IdeLockfileInfo if successfully parsed, None otherwise.
    """
    try:
        content = path.read_text(encoding="utf-8")

        workspace_folders: list[str] = []
        pid: int | None = None
        ide_name: str | None = None
        use_web_socket = False
        running_in_windows = False
        auth_token: str | None = None

        try:
            parsed = json.loads(content)
            workspace_folders = parsed.get("workspaceFolders", [])
            pid = parsed.get("pid")
            ide_name = parsed.get("ideName")
            use_web_socket = parsed.get("transport") == "ws"
            running_in_windows = parsed.get("runningInWindows", False) is True
            auth_token = parsed.get("authToken")
        except (json.JSONDecodeError, TypeError):
            # Older format: just a list of paths (one per line)
            workspace_folders = [line.strip() for line in content.split("\n") if line.strip()]

        # Extract port from filename (e.g., "12345.lock" -> 12345)
        filename = path.name
        port_str = filename.replace(".lock", "")
        try:
            port = int(port_str)
        except ValueError:
            return None

        return IdeLockfileInfo(
            workspace_folders=workspace_folders,
            port=port,
            pid=pid,
            ide_name=ide_name,
            use_web_socket=use_web_socket,
            running_in_windows=running_in_windows,
            auth_token=auth_token,
        )
    except OSError as e:
        logger.debug(f"[bridge:ide] Failed to read lockfile {path}: {e}")
        return None


def get_sorted_ide_lockfiles() -> list[Path]:
    """Get IDE lockfiles sorted by modification time (newest first).

    Returns:
        List of lockfile paths sorted by mtime descending.
    """
    lockfile_dir = get_ide_lockfile_dir()
    if not lockfile_dir.exists():
        return []

    try:
        entries = list(lockfile_dir.iterdir())
        lock_entries = [e for e in entries if e.is_file() and e.name.endswith(".lock")]

        # Stat all lockfiles
        lock_infos: list[tuple[Path, float]] = []
        for entry in lock_entries:
            try:
                mtime = entry.stat().st_mtime
                lock_infos.append((entry, mtime))
            except OSError:
                pass

        # Sort by mtime descending (newest first)
        lock_infos.sort(key=lambda x: x[1], reverse=True)
        return [p for p, _ in lock_infos]
    except OSError as e:
        logger.debug(f"[bridge:ide] Failed to list lockfile directory: {e}")
        return []


# =============================================================================
# Connection Checking
# =============================================================================


def check_ide_connection(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if an IDE connection is responding.

    Args:
        host: Host to connect to.
        port: Port to connect to.
        timeout: Connection timeout in seconds.

    Returns:
        True if the port is open and responding.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except OSError:
        return False


def is_process_running(pid: int) -> bool:
    """Check if a process with the given PID is running.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process is running.
    """
    if pid <= 0:
        return False
    try:
        # On Unix, signal 0 checks if process exists
        if sys.platform != "win32":
            os.kill(pid, 0)
        else:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                exit_code = ctypes.DWORD()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                return exit_code.value == STILL_ACTIVE
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def detect_host_ip(is_ide_running_in_windows: bool, port: int) -> str:
    """Detect the host IP to use for IDE connection.

    Args:
        is_ide_running_in_windows: Whether the IDE is running in Windows (WSL context).
        port: Port number (used for caching).

    Returns:
        The host IP address to use.
    """
    # Check for override
    override = os.environ.get("CLAUDE_CODE_IDE_HOST_OVERRIDE")
    if override:
        return override

    platform = get_platform()
    if platform != "wsl" or not is_ide_running_in_windows:
        return "127.0.0.1"

    # WSL2 trying to connect to Windows IDE: use default gateway
    try:
        result = subprocess.run(
            ["ip", "route", "show"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "default" in line or "via" in line:
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] == "default":
                        gateway = parts[2]
                        # Verify gateway is reachable on the port
                        if check_ide_connection(gateway, port):
                            return gateway
    except (OSError, subprocess.TimeoutExpired):
        pass

    return "127.0.0.1"


# =============================================================================
# IDE Detection
# =============================================================================


def _normalize_path(path: str) -> str:
    """Normalize a path for comparison (NFC Unicode form).

    Args:
        path: Path string to normalize.

    Returns:
        Normalized path string.
    """
    import unicodedata

    return unicodedata.normalize("NFC", path)


def _path_contains(path: str, prefix: str) -> bool:
    """Check if path starts with prefix (handles trailing separators).

    Args:
        path: The path to check.
        prefix: The prefix to match.

    Returns:
        True if path equals prefix or starts with prefix + separator.
    """
    if path == prefix:
        return True
    return path.startswith(prefix + os.sep) or path.startswith(prefix + "/")


def _is_cwd_in_workspace(cwd: str, workspace_folders: list[str]) -> bool:
    """Check if the current working directory is within any workspace folder.

    Args:
        cwd: Current working directory.
        workspace_folders: List of workspace folder paths.

    Returns:
        True if cwd is within one of the workspace folders.
    """
    normalized_cwd = _normalize_path(cwd)

    for wf in workspace_folders:
        if not wf:
            continue
        normalized_wf = _normalize_path(wf)

        if _path_contains(normalized_cwd, normalized_wf):
            return True

    return False


def detect_ides(
    include_invalid: bool = False,
    cwd: str | None = None,
) -> list[DetectedIDEInfo]:
    """Detect IDEs that have a running Claude Code extension.

    Args:
        include_invalid: If True, also return IDEs whose workspace doesn't match cwd.
        cwd: Current working directory. Defaults to os.getcwd().

    Returns:
        List of detected IDEs with their connection information.
    """
    detected: list[DetectedIDEInfo] = []

    try:
        # Get env port override
        sse_port_str = os.environ.get("CLAUDE_CODE_SSE_PORT")
        env_port: int | None = int(sse_port_str) if sse_port_str else None

        # Get current working directory
        work_dir = cwd or os.getcwd()
        normalized_cwd = _normalize_path(work_dir)

        # Get and read lockfiles
        lockfile_paths = get_sorted_ide_lockfiles()
        lockfile_infos: list[IdeLockfileInfo | None] = []
        for lockfile_path in lockfile_paths:
            lockfile_infos.append(read_ide_lockfile(lockfile_path))

        for _lockfile_path, lockfile_info in zip(lockfile_paths, lockfile_infos, strict=True):
            if lockfile_info is None:
                continue

            # Validate workspace
            is_valid = False
            if env_port is not None and lockfile_info.port == env_port:
                # Port matches env var: always valid
                is_valid = True
            elif _is_cwd_in_workspace(normalized_cwd, lockfile_info.workspace_folders):
                is_valid = True

            if not is_valid and not include_invalid:
                continue

            # Check if process is still running (skip if PID available and dead)
            if lockfile_info.pid and not is_process_running(lockfile_info.pid):
                # Process dead, but still include if include_invalid
                if not include_invalid:
                    continue

            # Build URL
            host = detect_host_ip(lockfile_info.running_in_windows, lockfile_info.port)
            if lockfile_info.use_web_socket:
                url = f"ws://{host}:{lockfile_info.port}"
            else:
                url = f"http://{host}:{lockfile_info.port}/sse"

            ide_name = lockfile_info.ide_name or "IDE"

            detected.append(
                DetectedIDEInfo(
                    name=ide_name,
                    port=lockfile_info.port,
                    workspace_folders=lockfile_info.workspace_folders,
                    url=url,
                    is_valid=is_valid,
                    auth_token=lockfile_info.auth_token,
                    ide_running_in_windows=lockfile_info.running_in_windows,
                )
            )

        # If env port is set and there's a match, filter to just that one
        if not include_invalid and env_port is not None:
            env_port_matches = [ide for ide in detected if ide.is_valid and ide.port == env_port]
            if len(env_port_matches) == 1:
                return env_port_matches

    except Exception as e:
        logger.debug(f"[bridge:ide] IDE detection failed: {e}")

    return detected


# =============================================================================
# IDE Cleanup
# =============================================================================


def cleanup_stale_ide_lockfiles() -> int:
    """Remove stale IDE lockfiles for dead processes or unreachable ports.

    Returns:
        Number of lockfiles removed.
    """
    removed = 0
    try:
        lockfile_paths = get_sorted_ide_lockfiles()
        for lockfile_path in lockfile_paths:
            lockfile_info = read_ide_lockfile(lockfile_path)
            if lockfile_info is None:
                # Can't read: delete it
                try:
                    lockfile_path.unlink()
                    removed += 1
                except OSError:
                    pass
                continue

            # Check if port is responding
            host = detect_host_ip(lockfile_info.running_in_windows, lockfile_info.port)
            is_responding = check_ide_connection(host, lockfile_info.port)

            should_delete = False
            if lockfile_info.pid:
                # Has PID: check if process is running
                if not is_process_running(lockfile_info.pid):
                    if not is_responding:
                        should_delete = True
            else:
                # No PID: check port directly
                if not is_responding:
                    should_delete = True

            if should_delete:
                try:
                    lockfile_path.unlink()
                    removed += 1
                except OSError:
                    pass
    except Exception as e:
        logger.debug(f"[bridge:ide] Lockfile cleanup failed: {e}")

    return removed


# =============================================================================
# IDE Type Utilities
# =============================================================================


def is_vscode_ide(ide: IdeType | None) -> bool:
    """Check if an IDE type is VS Code-based.

    Args:
        ide: The IDE type to check.

    Returns:
        True if the IDE is VS Code, Cursor, or Windsurf.
    """
    if ide is None:
        return False
    config = SUPPORTED_IDE_CONFIGS.get(ide)
    return config is not None and config.ide_kind == IdeKind.VSCODE


def is_jetbrains_ide(ide: IdeType | None) -> bool:
    """Check if an IDE type is a JetBrains IDE.

    Args:
        ide: The IDE type to check.

    Returns:
        True if the IDE is a JetBrains product.
    """
    if ide is None:
        return False
    config = SUPPORTED_IDE_CONFIGS.get(ide)
    return config is not None and config.ide_kind == IdeKind.JETBRAINS


def get_ide_display_name(ide: IdeType | str | None) -> str:
    """Get the display name for an IDE type.

    Args:
        ide: The IDE type or terminal name.

    Returns:
        Display name string.
    """
    if ide is None:
        return "IDE"

    # Try as IdeType first
    if isinstance(ide, IdeType):
        config = SUPPORTED_IDE_CONFIGS.get(ide)
        if config:
            return config.display_name

    # Try as string key
    if isinstance(ide, str):
        try:
            ide_type = IdeType(ide)
            config = SUPPORTED_IDE_CONFIGS.get(ide_type)
            if config:
                return config.display_name
        except ValueError:
            pass

    # Fallback: capitalize
    return ide.replace("-", " ").replace("_", " ").title()


# =============================================================================
# Process-based IDE Detection
# =============================================================================


def detect_running_ides() -> list[IdeType]:
    """Detect IDEs by checking running processes.

    Returns:
        List of IDE types that have running processes.
    """
    detected: list[IdeType] = []
    platform = get_platform()

    try:
        if platform == "macos":
            # Use ps to get process list
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            output = result.stdout.lower()
        elif platform == "windows":
            # Use tasklist
            result = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            output = result.stdout.lower()
        elif platform in ("linux", "wsl"):
            # Use ps to get process list
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            output = result.stdout.lower()
        else:
            return []
    except (OSError, subprocess.TimeoutExpired):
        return []

    # Search for each IDE's process keywords
    for ide_type, config in SUPPORTED_IDE_CONFIGS.items():
        keywords: list[str]
        if platform == "macos":
            keywords = config.process_keywords_mac
        elif platform == "windows":
            keywords = config.process_keywords_windows
        else:
            keywords = config.process_keywords_linux

        if not keywords:
            continue

        for keyword in keywords:
            if keyword.lower() in output:
                detected.append(ide_type)
                break

    return detected


# =============================================================================
# VS Code Extension Detection
# =============================================================================


def is_vscode_extension_installed(ide_type: IdeType) -> bool:
    """Check if the Claude Code extension is installed in a VS Code-based IDE.

    Args:
        ide_type: The IDE type to check.

    Returns:
        True if the extension appears in --list-extensions output.
    """
    if not is_vscode_ide(ide_type):
        return False

    # Build the CLI command name
    cmd = _get_vscode_cli_command(ide_type)
    if cmd is None:
        return False

    try:
        result = subprocess.run(
            [cmd, "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout + result.stderr
        return "anthropic.claude-code" in output.lower()
    except (OSError, subprocess.TimeoutExpired):
        return False


def _get_vscode_cli_command(ide_type: IdeType) -> str | None:
    """Get the CLI command name for a VS Code-based IDE.

    Args:
        ide_type: The IDE type.

    Returns:
        CLI command name or None.
    """
    if not is_vscode_ide(ide_type):
        return None

    ext = ".cmd" if sys.platform == "win32" else ""
    if ide_type == IdeType.VSCODE:
        return f"code{ext}"
    if ide_type == IdeType.CURSOR:
        return f"cursor{ext}"
    if ide_type == IdeType.WINDSURF:
        return f"windsurf{ext}"
    return None
