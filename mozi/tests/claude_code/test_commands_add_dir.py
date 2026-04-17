"""
Tests for commands/add_dir.py - Add directory command.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.add_dir import AddDirCommand
from claude_code.commands.base import CommandType


class TestAddDirCommand:
    """Tests for AddDirCommand."""

    def test_create(self) -> None:
        """Test creating AddDirCommand."""
        cmd = AddDirCommand()
        assert cmd.name == "add-dir"
        assert cmd.description == "Add a directory to the workspace"
        assert cmd.argument_hint == "<path>"
        assert cmd.command_type == CommandType.LOCAL_JSX

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = AddDirCommand()
        assert "/add-dir" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_no_args_returns_form(self) -> None:
        """Test execute with no arguments returns input form."""
        cmd = AddDirCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "AddWorkspaceDirectory"
        assert "onAddDirectory" in result.node["props"]
        assert "onCancel" in result.node["props"]

    @pytest.mark.asyncio
    async def test_execute_nonexistent_directory(self) -> None:
        """Test execute with non-existent directory."""
        cmd = AddDirCommand()
        result = await cmd.execute("/nonexistent/path", {})

        assert result.type == "text"
        assert "Directory not found" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_file_not_directory(self) -> None:
        """Test execute with a file instead of directory."""
        with tempfile.NamedTemporaryFile() as f:
            cmd = AddDirCommand()
            result = await cmd.execute(f.name, {})

            assert result.type == "text"
            assert "Not a directory" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_valid_directory(self) -> None:
        """Test execute with valid directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = AddDirCommand()
            result = await cmd.execute(tmpdir, {})

            assert result.type == "jsx"
            assert result.node is not None
            assert result.node["type"] == "AddWorkspaceDirectory"
            assert result.node["props"]["directoryPath"] == os.path.abspath(tmpdir)
