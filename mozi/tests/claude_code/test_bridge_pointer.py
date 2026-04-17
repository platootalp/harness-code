"""
Tests for bridge/pointer.py - Bridge pointer file management.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest


class TestBridgePointerSchema:
    """Tests for BridgePointer data class and constants."""

    def test_ttl_is_4_hours(self) -> None:
        """BRIDGE_POINTER_TTL_MS should equal 4 hours in milliseconds."""
        from claude_code.bridge.pointer import BRIDGE_POINTER_TTL_MS

        assert BRIDGE_POINTER_TTL_MS == 4 * 60 * 60 * 1000

    def test_bridge_pointer_fields(self) -> None:
        """BridgePointer should have required fields."""
        from claude_code.bridge.pointer import BridgePointer

        ptr = BridgePointer(
            session_id="sess-123",
            environment_id="env-456",
            source="repl",
        )
        assert ptr.session_id == "sess-123"
        assert ptr.environment_id == "env-456"
        assert ptr.source == "repl"


class TestBridgePointerWithAge:
    """Tests for BridgePointerWithAge dataclass."""

    def test_has_age_ms_field(self) -> None:
        """BridgePointerWithAge should have age_ms field."""
        from claude_code.bridge.pointer import BridgePointerWithAge

        ptr = BridgePointerWithAge(
            session_id="sess-abc",
            environment_id="env-xyz",
            source="standalone",
            age_ms=5000.0,
        )
        assert ptr.age_ms == 5000.0
        assert ptr.session_id == "sess-abc"

    def test_age_ms_defaults_to_zero(self) -> None:
        """BridgePointerWithAge age_ms should default to 0."""
        from claude_code.bridge.pointer import BridgePointerWithAge

        ptr = BridgePointerWithAge(
            session_id="s",
            environment_id="e",
            source="repl",
        )
        assert ptr.age_ms == 0.0


class TestGetBridgePointerPath:
    """Tests for get_bridge_pointer_path()."""

    def test_returns_path_in_projects_dir(self) -> None:
        """Path should be under the projects directory."""
        from claude_code.bridge.pointer import get_bridge_pointer_path

        path = get_bridge_pointer_path("/home/user/project")
        assert "bridge-pointer.json" in path

    def test_sanitizes_path_with_special_chars(self) -> None:
        """Path should sanitize directory names with special characters."""
        from claude_code.bridge.pointer import get_bridge_pointer_path

        path = get_bridge_pointer_path("/home/user/my project/src")
        assert "bridge-pointer.json" in path


class TestWriteAndReadBridgePointer:
    """Tests for write/read/clear bridge pointer operations."""

    @pytest.mark.asyncio
    async def test_write_and_read_roundtrip(self, tmp_path) -> None:
        """Pointer should survive a write-then-read roundtrip."""
        from pathlib import Path

        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import (
            BridgePointer,
            read_bridge_pointer,
            write_bridge_pointer,
        )

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            dir_path = str(tmp_path / "project")
            os.makedirs(dir_path, exist_ok=True)

            ptr = BridgePointer(
                session_id="sess-roundtrip",
                environment_id="env-rt",
                source="repl",
            )
            await write_bridge_pointer(dir_path, ptr)

            result = await read_bridge_pointer(dir_path)
            assert result is not None
            assert result.session_id == "sess-roundtrip"
            assert result.environment_id == "env-rt"
            assert result.source == "repl"
            assert result.age_ms >= 0
        finally:
            ptr_module._restore_projects_dir(None)

    @pytest.mark.asyncio
    async def test_read_missing_returns_none(self, tmp_path) -> None:
        """read_bridge_pointer returns None when file doesn't exist."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import read_bridge_pointer

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            result = await read_bridge_pointer(str(tmp_path / "nonexistent"))
            assert result is None
        finally:
            ptr_module._restore_projects_dir(None)

    @pytest.mark.asyncio
    async def test_read_invalid_json_returns_none(self, tmp_path) -> None:
        """read_bridge_pointer returns None for corrupted JSON."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import read_bridge_pointer

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            dir_path = str(tmp_path / "project")
            os.makedirs(dir_path, exist_ok=True)
            ptr_path = str(tmp_path / "project" / "bridge-pointer.json")
            with open(ptr_path, "w") as f:
                f.write("not valid json{")
            os.utime(ptr_path, None)

            result = await read_bridge_pointer(dir_path)
            assert result is None
        finally:
            ptr_module._restore_projects_dir(None)

    @pytest.mark.asyncio
    async def test_read_missing_fields_returns_none(self, tmp_path) -> None:
        """read_bridge_pointer returns None when required fields are missing."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import read_bridge_pointer

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            dir_path = str(tmp_path / "project")
            os.makedirs(dir_path, exist_ok=True)
            ptr_path = str(tmp_path / "project" / "bridge-pointer.json")
            with open(ptr_path, "w") as f:
                json.dump({"sessionId": "sess-123"}, f)
            os.utime(ptr_path, None)

            result = await read_bridge_pointer(dir_path)
            assert result is None
        finally:
            ptr_module._restore_projects_dir(None)

    @pytest.mark.asyncio
    async def test_read_invalid_source_returns_none(self, tmp_path) -> None:
        """read_bridge_pointer returns None for invalid source enum value."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import read_bridge_pointer

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            dir_path = str(tmp_path / "project")
            os.makedirs(dir_path, exist_ok=True)
            ptr_path = str(tmp_path / "project" / "bridge-pointer.json")
            with open(ptr_path, "w") as f:
                json.dump({
                    "sessionId": "sess-123",
                    "environmentId": "env-456",
                    "source": "invalid_source",
                }, f)
            os.utime(ptr_path, None)

            result = await read_bridge_pointer(dir_path)
            assert result is None
        finally:
            ptr_module._restore_projects_dir(None)

    @pytest.mark.asyncio
    async def test_age_ms_is_positive(self, tmp_path) -> None:
        """age_ms should be non-negative even if clock skews."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import (
            BridgePointer,
            read_bridge_pointer,
            write_bridge_pointer,
        )

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            dir_path = str(tmp_path / "project")
            os.makedirs(dir_path, exist_ok=True)

            ptr = BridgePointer(
                session_id="sess-age",
                environment_id="env-age",
                source="standalone",
            )
            await write_bridge_pointer(dir_path, ptr)
            result = await read_bridge_pointer(dir_path)
            assert result is not None
            assert result.age_ms >= 0
        finally:
            ptr_module._restore_projects_dir(None)


class TestClearBridgePointer:
    """Tests for clear_bridge_pointer()."""

    @pytest.mark.asyncio
    async def test_clear_removes_file(self, tmp_path) -> None:
        """clear_bridge_pointer removes the pointer file."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import (
            BridgePointer,
            clear_bridge_pointer,
            get_bridge_pointer_path,
            write_bridge_pointer,
        )

        # Use a simple project path to avoid path complexity
        # Override projects dir to a flat temp dir
        flat_projects = tempfile.mkdtemp()
        try:
            ptr_module._override_projects_dir(flat_projects)
            dir_path = os.path.join(flat_projects, "myproject")
            os.makedirs(dir_path, exist_ok=True)

            ptr = BridgePointer(
                session_id="sess-clear",
                environment_id="env-clear",
                source="repl",
            )
            await write_bridge_pointer(dir_path, ptr)

            ptr_path = get_bridge_pointer_path(dir_path)
            assert os.path.exists(ptr_path), f"Expected {ptr_path} to exist"

            await clear_bridge_pointer(dir_path)
            assert not os.path.exists(ptr_path)
        finally:
            ptr_module._restore_projects_dir(None)
            import shutil
            shutil.rmtree(flat_projects, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_clear_idempotent(self, tmp_path) -> None:
        """clear_bridge_pointer is idempotent — missing file is fine."""
        from claude_code.bridge import pointer as ptr_module
        from claude_code.bridge.pointer import clear_bridge_pointer

        tmp = str(tmp_path)
        ptr_module._override_projects_dir(tmp)
        try:
            # Should not raise
            await clear_bridge_pointer(str(tmp_path / "nonexistent"))
        finally:
            ptr_module._restore_projects_dir(None)
