"""Tests for bridge/ide.py - IDE detection for bridge connections."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claude_code.bridge.ide import (
    SUPPORTED_IDE_CONFIGS,
    DetectedIDEInfo,
    IdeConfig,
    IdeKind,
    IdeLockfileInfo,
    IdeType,
    _is_cwd_in_workspace,
    _normalize_path,
    _path_contains,
    check_ide_connection,
    cleanup_stale_ide_lockfiles,
    detect_host_ip,
    detect_ides,
    detect_running_ides,
    get_claude_config_home,
    get_ide_display_name,
    get_ide_lockfile_dir,
    get_platform,
    get_sorted_ide_lockfiles,
    is_jetbrains_ide,
    is_process_running,
    is_vscode_extension_installed,
    is_vscode_ide,
    read_ide_lockfile,
)

# =============================================================================
# IdeType Tests
# =============================================================================


class TestIdeType:
    def test_ide_types_exist(self) -> None:
        """All expected IDE types should exist."""
        expected = {
            "cursor",
            "windsurf",
            "vscode",
            "pycharm",
            "intellij",
            "webstorm",
            "phpstorm",
            "rubymine",
            "clion",
            "goland",
            "rider",
            "datagrip",
            "appcode",
            "dataspell",
            "aqua",
            "gateway",
            "fleet",
            "androidstudio",
        }
        actual = {t.value for t in IdeType}
        assert actual == expected

    def test_ide_types_are_strings(self) -> None:
        """IdeType values should be strings (StrEnum)."""
        for t in IdeType:
            assert isinstance(t, str)


# =============================================================================
# IdeKind Tests
# =============================================================================


class TestIdeKind:
    def test_ide_kinds_exist(self) -> None:
        """IdeKind should have vscode and jetbrains."""
        assert IdeKind.VSCODE == "vscode"
        assert IdeKind.JETBRAINS == "jetbrains"


# =============================================================================
# SUPPORTED_IDE_CONFIGS Tests
# =============================================================================


class TestSupportedIdeConfigs:
    def test_all_configs_have_kind(self) -> None:
        """Every IDE config should have a valid IdeKind."""
        for _ide_type, config in SUPPORTED_IDE_CONFIGS.items():
            assert isinstance(config, IdeConfig)
            assert isinstance(config.ide_kind, IdeKind)
            assert config.display_name

    def test_vscode_kinds(self) -> None:
        """VS Code-based IDEs should have VSCODE kind."""
        vscode_types = {IdeType.VSCODE, IdeType.CURSOR, IdeType.WINDSURF}
        for t in vscode_types:
            assert t in SUPPORTED_IDE_CONFIGS
            assert SUPPORTED_IDE_CONFIGS[t].ide_kind == IdeKind.VSCODE

    def test_jetbrains_kinds(self) -> None:
        """JetBrains IDEs should have JETBRAINS kind."""
        jetbrains_types = {
            IdeType.PYCHARM,
            IdeType.INTELLIJ,
            IdeType.WEBSTORM,
            IdeType.PHPSTORM,
            IdeType.RUBYMINE,
            IdeType.CLION,
            IdeType.GOLAND,
            IdeType.RIDER,
            IdeType.DATAGRIP,
            IdeType.APPCODE,
            IdeType.DATASPELL,
            IdeType.AQUA,
            IdeType.GATEWAY,
            IdeType.FLEET,
            IdeType.ANDROIDSTUDIO,
        }
        for t in jetbrains_types:
            assert t in SUPPORTED_IDE_CONFIGS
            assert SUPPORTED_IDE_CONFIGS[t].ide_kind == IdeKind.JETBRAINS


# =============================================================================
# IdeLockfileInfo Tests
# =============================================================================


class TestIdeLockfileInfo:
    def test_defaults(self) -> None:
        """IdeLockfileInfo should have correct defaults."""
        info = IdeLockfileInfo(workspace_folders=["/tmp"], port=8080)
        assert info.workspace_folders == ["/tmp"]
        assert info.port == 8080
        assert info.pid is None
        assert info.ide_name is None
        assert info.use_web_socket is False
        assert info.running_in_windows is False
        assert info.auth_token is None

    def test_full(self) -> None:
        """IdeLockfileInfo should accept all fields."""
        info = IdeLockfileInfo(
            workspace_folders=["/home/user/project"],
            port=9222,
            pid=12345,
            ide_name="Cursor",
            use_web_socket=True,
            running_in_windows=True,
            auth_token="secret-token",
        )
        assert info.pid == 12345
        assert info.ide_name == "Cursor"
        assert info.use_web_socket is True
        assert info.running_in_windows is True
        assert info.auth_token == "secret-token"


# =============================================================================
# DetectedIDEInfo Tests
# =============================================================================


class TestDetectedIDEInfo:
    def test_defaults(self) -> None:
        """DetectedIDEInfo should have correct defaults."""
        info = DetectedIDEInfo(
            name="Cursor",
            port=8080,
            workspace_folders=["/tmp"],
            url="http://127.0.0.1:8080/sse",
            is_valid=True,
        )
        assert info.auth_token is None
        assert info.ide_running_in_windows is None

    def test_full(self) -> None:
        """DetectedIDEInfo should accept all fields."""
        info = DetectedIDEInfo(
            name="VS Code",
            port=9222,
            workspace_folders=["/home/user/project"],
            url="ws://127.0.0.1:9222",
            is_valid=True,
            auth_token="abc123",
            ide_running_in_windows=True,
        )
        assert info.auth_token == "abc123"
        assert info.ide_running_in_windows is True


# =============================================================================
# Platform Detection Tests
# =============================================================================


class TestGetPlatform:
    def test_macos(self) -> None:
        """Should return 'macos' on Darwin."""
        with patch.object(sys, "platform", "darwin"):
            assert get_platform() == "macos"

    def test_windows(self) -> None:
        """Should return 'windows' on Win32."""
        with patch.object(sys, "platform", "win32"):
            assert get_platform() == "windows"

    def test_linux(self) -> None:
        """Should return 'linux' on Linux."""
        with patch.object(sys, "platform", "linux"), patch(
            "pathlib.Path.exists", return_value=False
        ):
            assert get_platform() == "linux"

    def test_wsl(self) -> None:
        """Should return 'wsl' when /proc/version contains microsoft."""
        # We need to patch os.path.exists AND the Path call
        # Since we're on darwin, sys.platform != "linux" so we also need
        # to patch sys.platform
        with patch.object(sys, "platform", "linux2"), patch.object(
            os.path, "exists", return_value=True
        ), patch(
            "claude_code.bridge.ide.Path.read_text",
            return_value="microsoft\nwsl",
        ):
            assert get_platform() == "wsl"


# =============================================================================
# Config Home Tests
# =============================================================================


class TestClaudeConfigHome:
    def test_macos(self) -> None:
        """Should return macOS config path."""
        with patch.object(sys, "platform", "darwin"):
            home = get_claude_config_home()
            assert home == Path.home() / "Library" / "Application Support" / "claude"

    def test_windows(self) -> None:
        """Should return Windows config path."""
        with patch.object(sys, "platform", "win32"), patch.dict(
            os.environ, {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}
        ):
            home = get_claude_config_home()
            assert "Users" in str(home)
            assert "claude" in str(home)

    def test_linux(self) -> None:
        """Should return Linux config path."""
        with patch.object(sys, "platform", "linux"):
            home = get_claude_config_home()
            assert home == Path.home() / ".claude"


# =============================================================================
# Lockfile Reading Tests
# =============================================================================


class TestReadIdeLockfile:
    def test_parse_json_format(self, tmp_path: Path) -> None:
        """Should parse JSON format lockfiles."""
        lockfile = tmp_path / "8080.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": ["/home/user/project"],
                    "pid": 12345,
                    "ideName": "Cursor",
                    "transport": "ws",
                    "runningInWindows": True,
                    "authToken": "secret123",
                }
            )
        )
        info = read_ide_lockfile(lockfile)
        assert info is not None
        assert info.port == 8080
        assert info.workspace_folders == ["/home/user/project"]
        assert info.pid == 12345
        assert info.ide_name == "Cursor"
        assert info.use_web_socket is True
        assert info.running_in_windows is True
        assert info.auth_token == "secret123"

    def test_parse_legacy_line_format(self, tmp_path: Path) -> None:
        """Should parse legacy line-by-line format."""
        lockfile = tmp_path / "9090.lock"
        lockfile.write_text("/home/user/project\n/tmp/other\n")
        info = read_ide_lockfile(lockfile)
        assert info is not None
        assert info.port == 9090
        assert info.workspace_folders == ["/home/user/project", "/tmp/other"]
        assert info.pid is None
        assert info.use_web_socket is False

    def test_invalid_port(self, tmp_path: Path) -> None:
        """Should return None for non-numeric port in filename."""
        lockfile = tmp_path / "abc.lock"
        lockfile.write_text(json.dumps({"workspaceFolders": []}))
        assert read_ide_lockfile(lockfile) is None

    def test_missing_file(self, tmp_path: Path) -> None:
        """Should return None for non-existent file."""
        assert read_ide_lockfile(tmp_path / "nonexistent.lock") is None

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Should fall back to line parsing for invalid JSON."""
        lockfile = tmp_path / "7070.lock"
        lockfile.write_text("/workspace/project\n")
        info = read_ide_lockfile(lockfile)
        assert info is not None
        assert info.port == 7070


# =============================================================================
# Lockfile Listing Tests
# =============================================================================


class TestGetSortedIdeLockfiles:
    def test_returns_empty_when_dir_missing(self, tmp_path: Path) -> None:
        """Should return empty list when IDE lockfile dir doesn't exist."""
        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir",
            return_value=tmp_path / "nonexistent",
        ):
            assert get_sorted_ide_lockfiles() == []

    def test_returns_lockfiles_sorted_by_mtime(self, tmp_path: Path) -> None:
        """Should return lockfiles sorted by modification time (newest first)."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        old_file = lock_dir / "1111.lock"
        old_file.write_text('["/old"]')
        new_file = lock_dir / "2222.lock"
        new_file.write_text('["/new"]')

        # Make new_file newer
        import time

        time.sleep(0.01)
        new_file.touch()

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ):
            result = get_sorted_ide_lockfiles()

        assert len(result) == 2
        # Newest first
        assert result[0].name == "2222.lock"
        assert result[1].name == "1111.lock"


# =============================================================================
# Connection Checking Tests
# =============================================================================


class TestCheckIdeConnection:
    def test_open_port(self) -> None:
        """Should return True when port is open."""
        # Create a temporary server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]

        try:
            assert check_ide_connection("127.0.0.1", port, timeout=0.5) is True
        finally:
            server_sock.close()

    def test_closed_port(self) -> None:
        """Should return False when port is closed."""
        assert check_ide_connection("127.0.0.1", 1, timeout=0.1) is False

    def test_connection_timeout(self) -> None:
        """Should return False on connection error."""
        assert (
            check_ide_connection("192.0.2.1", 12345, timeout=0.01) is False
        )  # TEST-NET


# =============================================================================
# Process Checking Tests
# =============================================================================


class TestIsProcessRunning:
    def test_invalid_pid(self) -> None:
        """Should return False for invalid PIDs."""
        assert is_process_running(0) is False
        assert is_process_running(-1) is False

    def test_own_process(self) -> None:
        """Should return True for current process."""
        assert is_process_running(os.getpid()) is True


# =============================================================================
# Path Utilities Tests
# =============================================================================


class TestNormalizePath:
    def test_returns_normalized_path(self) -> None:
        """Should return NFC-normalized path."""
        result = _normalize_path("/home/user")
        assert isinstance(result, str)
        assert result == "/home/user"


class TestPathContains:
    def test_exact_match(self) -> None:
        """Should match exact path."""
        assert _path_contains("/home/user", "/home/user") is True

    def test_with_separator(self) -> None:
        """Should match with separator."""
        assert _path_contains("/home/user/project", "/home/user") is True
        assert _path_contains("/home/user/project", "/home") is True

    def test_no_match(self) -> None:
        """Should not match unrelated paths."""
        assert _path_contains("/home/user", "/home/other") is False
        assert _path_contains("/home/user", "/home/userx") is False

    def test_prefix_not_dir(self) -> None:
        """Should not match when prefix looks similar but isn't a parent."""
        assert _path_contains("/home/userx", "/home/user") is False


class TestIsCwdInWorkspace:
    def test_exact_match(self) -> None:
        """Should match when cwd equals workspace folder."""
        assert _is_cwd_in_workspace("/project", ["/project"]) is True

    def test_subdirectory(self) -> None:
        """Should match when cwd is a subdirectory."""
        assert _is_cwd_in_workspace("/project/src", ["/project"]) is True
        assert _is_cwd_in_workspace("/project/src/claude_code", ["/project/src"]) is True

    def test_no_match(self) -> None:
        """Should not match unrelated paths."""
        assert _is_cwd_in_workspace("/project", ["/other"]) is False

    def test_empty_workspace_folders(self) -> None:
        """Should not match with empty workspace list."""
        assert _is_cwd_in_workspace("/project", []) is False

    def test_empty_workspace_entry(self) -> None:
        """Should skip empty workspace entries."""
        assert _is_cwd_in_workspace("/project", ["", "/other"]) is False


# =============================================================================
# Host IP Detection Tests
# =============================================================================


class TestDetectHostIp:
    def test_override_env(self) -> None:
        """Should return override from environment variable."""
        with patch.dict(os.environ, {"CLAUDE_CODE_IDE_HOST_OVERRIDE": "192.168.1.1"}):
            assert detect_host_ip(False, 8080) == "192.168.1.1"

    def test_non_wsl(self) -> None:
        """Should return 127.0.0.1 on non-WSL platforms."""
        with patch(
            "claude_code.bridge.ide.get_platform", return_value="linux"
        ):
            assert detect_host_ip(False, 8080) == "127.0.0.1"

    def test_wsl_windows_ide(self) -> None:
        """Should return gateway IP in WSL when connecting to Windows IDE."""
        with patch(
            "claude_code.bridge.ide.get_platform", return_value="wsl"
        ), patch(
            "claude_code.bridge.ide.check_ide_connection",
            return_value=True,
        ), patch(
            "subprocess.run",
            return_value=MagicMock(
                returncode=0,
                stdout="default via 172.17.0.1 dev eth0",
            ),
        ):
            result = detect_host_ip(True, 8080)
            assert result == "172.17.0.1"

    def test_wsl_fallback(self) -> None:
        """Should fallback to 127.0.0.1 when gateway lookup fails."""
        with patch(
            "claude_code.bridge.ide.get_platform", return_value="wsl"
        ), patch(
            "subprocess.run",
            side_effect=OSError,
        ):
            assert detect_host_ip(True, 8080) == "127.0.0.1"


# =============================================================================
# IDE Detection Tests
# =============================================================================


class TestDetectIdes:
    def test_returns_empty_when_no_lockfiles(self, tmp_path: Path) -> None:
        """Should return empty list when no lockfiles exist."""
        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir",
            return_value=tmp_path / "nonexistent",
        ):
            assert detect_ides(cwd="/tmp") == []

    def test_returns_matching_ides(self, tmp_path: Path) -> None:
        """Should return IDEs whose workspace contains cwd."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": [str(tmp_path)],
                    "ideName": "Cursor",
                }
            )
        )

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ), patch(
            "claude_code.bridge.ide.is_process_running", return_value=True
        ):
            result = detect_ides(cwd=str(tmp_path))

        assert len(result) == 1
        assert result[0].name == "Cursor"
        assert result[0].port == 8080
        assert result[0].is_valid is True

    def test_skips_invalid_ides(self, tmp_path: Path) -> None:
        """Should skip IDEs whose workspace doesn't match cwd by default."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": ["/completely/different/path"],
                    "ideName": "Cursor",
                }
            )
        )

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ):
            result = detect_ides(cwd=str(tmp_path))

        assert len(result) == 0

    def test_includes_invalid_when_requested(self, tmp_path: Path) -> None:
        """Should include invalid IDEs when include_invalid=True."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": ["/different/path"],
                    "ideName": "Cursor",
                }
            )
        )

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ):
            result = detect_ides(cwd=str(tmp_path), include_invalid=True)

        assert len(result) == 1
        assert result[0].is_valid is False

    def test_env_port_override(self, tmp_path: Path) -> None:
        """Should match by port from CLAUDE_CODE_SSE_PORT env var."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "9999.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": ["/other/path"],
                    "ideName": "VS Code",
                }
            )
        )

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ), patch.dict(os.environ, {"CLAUDE_CODE_SSE_PORT": "9999"}):
            result = detect_ides(cwd=str(tmp_path))

        assert len(result) == 1
        assert result[0].port == 9999
        assert result[0].is_valid is True

    def test_url_with_http(self, tmp_path: Path) -> None:
        """Should build SSE URL for HTTP transport."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": [str(tmp_path)],
                    "ideName": "Cursor",
                }
            )
        )

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ), patch(
            "claude_code.bridge.ide.is_process_running", return_value=True
        ):
            result = detect_ides(cwd=str(tmp_path))

        assert "http://127.0.0.1:8080/sse" in result[0].url

    def test_url_with_websocket(self, tmp_path: Path) -> None:
        """Should build WebSocket URL when transport is ws."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text(
            json.dumps(
                {
                    "workspaceFolders": [str(tmp_path)],
                    "ideName": "Cursor",
                    "transport": "ws",
                }
            )
        )

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ), patch(
            "claude_code.bridge.ide.is_process_running", return_value=True
        ):
            result = detect_ides(cwd=str(tmp_path))

        assert "ws://127.0.0.1:8080" in result[0].url


# =============================================================================
# Cleanup Tests
# =============================================================================


class TestCleanupStaleIdeLockfiles:
    def test_removes_unreadable_lockfiles(self, tmp_path: Path) -> None:
        """Should remove lockfiles that can't be read."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text("invalid content")
        # Make it unreadable by patching read_ide_lockfile to return None
        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ), patch(
            "claude_code.bridge.ide.read_ide_lockfile", return_value=None
        ):
            cleanup_stale_ide_lockfiles()

        # The file should be deleted
        assert not lockfile.exists()

    def test_keeps_responding_lockfiles(self, tmp_path: Path) -> None:
        """Should keep lockfiles with responding ports."""
        lock_dir = tmp_path / "ide"
        lock_dir.mkdir()

        lockfile = lock_dir / "8080.lock"
        lockfile.write_text(json.dumps({"workspaceFolders": []}))

        with patch(
            "claude_code.bridge.ide.get_ide_lockfile_dir", return_value=lock_dir
        ), patch(
            "claude_code.bridge.ide.read_ide_lockfile",
            return_value=IdeLockfileInfo(
                workspace_folders=["/tmp"],
                port=8080,
                pid=os.getpid(),
            ),
        ), patch(
            "claude_code.bridge.ide.check_ide_connection",
            return_value=True,
        ):
            removed = cleanup_stale_ide_lockfiles()

        assert removed == 0
        assert lockfile.exists()


# =============================================================================
# IDE Type Utilities Tests
# =============================================================================


class TestIsVscodeIde:
    def test_vscode_based(self) -> None:
        """Should return True for VS Code-based IDEs."""
        assert is_vscode_ide(IdeType.VSCODE) is True
        assert is_vscode_ide(IdeType.CURSOR) is True
        assert is_vscode_ide(IdeType.WINDSURF) is True

    def test_jetbrains(self) -> None:
        """Should return False for JetBrains IDEs."""
        assert is_vscode_ide(IdeType.PYCHARM) is False
        assert is_vscode_ide(IdeType.INTELLIJ) is False

    def test_none(self) -> None:
        """Should return False for None."""
        assert is_vscode_ide(None) is False


class TestIsJetbrainsIde:
    def test_jetbrains(self) -> None:
        """Should return True for JetBrains IDEs."""
        assert is_jetbrains_ide(IdeType.PYCHARM) is True
        assert is_jetbrains_ide(IdeType.INTELLIJ) is True
        assert is_jetbrains_ide(IdeType.WEBSTORM) is True
        assert is_jetbrains_ide(IdeType.CLION) is True

    def test_vscode_based(self) -> None:
        """Should return False for VS Code-based IDEs."""
        assert is_jetbrains_ide(IdeType.VSCODE) is False
        assert is_jetbrains_ide(IdeType.CURSOR) is False
        assert is_jetbrains_ide(IdeType.WINDSURF) is False

    def test_none(self) -> None:
        """Should return False for None."""
        assert is_jetbrains_ide(None) is False


class TestGetIdeDisplayName:
    def test_from_ide_type(self) -> None:
        """Should return display name from IdeType."""
        assert get_ide_display_name(IdeType.CURSOR) == "Cursor"
        assert get_ide_display_name(IdeType.VSCODE) == "VS Code"
        assert get_ide_display_name(IdeType.PYCHARM) == "PyCharm"

    def test_from_string(self) -> None:
        """Should return display name from string."""
        assert get_ide_display_name("cursor") == "Cursor"
        assert get_ide_display_name("pycharm") == "PyCharm"

    def test_none(self) -> None:
        """Should return 'IDE' for None."""
        assert get_ide_display_name(None) == "IDE"

    def test_unknown_ide(self) -> None:
        """Should capitalize unknown IDE names."""
        assert get_ide_display_name("unknown-ide") == "Unknown Ide"


# =============================================================================
# Process-based Detection Tests
# =============================================================================


class TestDetectRunningIdes:
    def test_macos_ps(self) -> None:
        """Should use ps on macOS."""
        with patch(
            "claude_code.bridge.ide.get_platform", return_value="macos"
        ), patch(
            "subprocess.run",
            return_value=MagicMock(
                returncode=0,
                stdout=" /Applications/Cursor.app/Contents/MacOS/Cursor",
            ),
        ):
            result = detect_running_ides()
            assert IdeType.CURSOR in result

    def test_linux_ps(self) -> None:
        """Should use ps on Linux."""
        with patch(
            "claude_code.bridge.ide.get_platform", return_value="linux"
        ), patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout="pycharm"),
        ):
            result = detect_running_ides()
            assert IdeType.PYCHARM in result

    def test_command_failure(self) -> None:
        """Should return empty list on command failure."""
        with patch(
            "claude_code.bridge.ide.get_platform", return_value="macos"
        ), patch(
            "subprocess.run",
            side_effect=OSError,
        ):
            assert detect_running_ides() == []


# =============================================================================
# VS Code Extension Tests
# =============================================================================


class TestIsVscodeExtensionInstalled:
    def test_vscode_based(self) -> None:
        """Should check extension for VS Code-based IDEs."""
        with patch(
            "claude_code.bridge.ide.is_vscode_ide", return_value=True
        ), patch(
            "claude_code.bridge.ide._get_vscode_cli_command",
            return_value="code",
        ), patch(
            "subprocess.run",
            return_value=MagicMock(
                returncode=0,
                stdout="anthropic.claude-code",
                stderr="",
            ),
        ):
            assert is_vscode_extension_installed(IdeType.VSCODE) is True

    def test_non_vscode(self) -> None:
        """Should return False for non-VS Code IDEs."""
        with patch(
            "claude_code.bridge.ide.is_vscode_ide", return_value=False
        ):
            assert is_vscode_extension_installed(IdeType.PYCHARM) is False
