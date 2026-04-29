"""
Tests for commands/init.py - Init command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.init import InitCommand
from claude_code.commands.base import CommandType


class TestInitCommand:
    """Tests for InitCommand (stub implementation)."""

    def test_create(self) -> None:
        """Test creating InitCommand."""
        cmd = InitCommand()
        assert cmd.name == "init"
        assert cmd.description == "Initialize Claude Code for a project"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is True

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = InitCommand()
        assert "/init" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = InitCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "InitWizard"
        assert "onDone" in result.node["props"]
