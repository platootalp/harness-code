"""
Tests for commands/ide.py - IDE command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.ide import IDECommand
from claude_code.commands.base import CommandType


class TestIDECommand:
    """Tests for IDECommand."""

    def test_create(self) -> None:
        """Test creating IDECommand."""
        cmd = IDECommand()
        assert cmd.name == "ide"
        assert cmd.description == "Manage IDE integrations and show status"
        assert cmd.argument_hint == "[open]"
        assert cmd.command_type == CommandType.LOCAL_JSX

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = IDECommand()
        assert "/ide" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_no_args_returns_panel(self) -> None:
        """Test execute with no arguments returns IDE panel."""
        cmd = IDECommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "IDEPanel"

    @pytest.mark.asyncio
    async def test_execute_open_returns_selection(self) -> None:
        """Test execute with 'open' argument returns IDE selection."""
        cmd = IDECommand()
        result = await cmd.execute("open", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "IDEOpenSelection"
        assert "availableIDEs" in result.node["props"]
        assert "onSelectIDE" in result.node["props"]

    @pytest.mark.asyncio
    async def test_execute_open_case_insensitive(self) -> None:
        """Test execute with uppercase 'open' works."""
        cmd = IDECommand()
        result = await cmd.execute("OPEN", {})

        assert result.type == "jsx"
        assert result.node["type"] == "IDEOpenSelection"
