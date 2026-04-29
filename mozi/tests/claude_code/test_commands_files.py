"""
Tests for commands/files.py - Files command.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.files import FilesCommand, _is_ant_user


class TestIsAntUser:
    """Tests for _is_ant_user helper."""

    def test_ant_user(self) -> None:
        """Test ANT user detection."""
        original = os.environ.get("USER_TYPE")
        try:
            os.environ["USER_TYPE"] = "ant"
            # Need to reimport to pick up env change
            from claude_code.commands.files import _is_ant_user as check
            assert check() is True
        finally:
            if original is None:
                os.environ.pop("USER_TYPE", None)
            else:
                os.environ["USER_TYPE"] = original

    def test_non_ant_user(self) -> None:
        """Test non-ANT user detection."""
        original = os.environ.get("USER_TYPE")
        try:
            os.environ.pop("USER_TYPE", None)
            from claude_code.commands.files import _is_ant_user as check
            assert check() is False
        finally:
            if original is not None:
                os.environ["USER_TYPE"] = original


class TestFilesCommand:
    """Tests for FilesCommand."""

    def test_create(self) -> None:
        """Test creating FilesCommand."""
        cmd = FilesCommand()
        assert cmd.name == "files"
        assert cmd.description == "Show files in the current context"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.supports_non_interactive is True

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = FilesCommand()
        help_text = cmd.get_help()
        assert "/files" in help_text

    def test_all_names(self) -> None:
        """Test _all_names."""
        cmd = FilesCommand()
        assert "files" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_no_files(self) -> None:
        """Test execute with no files in context."""
        cmd = FilesCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert result.value is not None
        assert "No files" in result.value

    @pytest.mark.asyncio
    async def test_execute_empty_list(self) -> None:
        """Test execute with empty list."""
        cmd = FilesCommand()
        mock_state = MagicMock()
        mock_state.__iter__ = MagicMock(return_value=iter([]))
        result = await cmd.execute("", {"readFileState": mock_state})
        assert result.type == "text"
        assert result.value is not None
        assert "No files" in result.value

    @pytest.mark.asyncio
    async def test_execute_with_files(self) -> None:
        """Test execute with files in context."""
        cmd = FilesCommand()
        mock_state = MagicMock()
        mock_state.__iter__ = MagicMock(return_value=iter(["/tmp/file1.py", "/tmp/file2.py"]))
        result = await cmd.execute("", {"readFileState": mock_state, "cwd": "/tmp"})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert result.value is not None
        assert "file1.py" in result.value
        assert "file2.py" in result.value

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that files command ignores arguments."""
        cmd = FilesCommand()
        result = await cmd.execute("--verbose", {})
        assert result.type == "text"
