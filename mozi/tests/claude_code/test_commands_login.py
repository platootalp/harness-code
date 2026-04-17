"""
Tests for commands/login.py - Login command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.login import LoginCommand
from claude_code.commands.base import CommandType


class TestLoginCommand:
    """Tests for LoginCommand."""

    def test_create(self) -> None:
        """Test creating LoginCommand."""
        cmd = LoginCommand()
        assert cmd.name == "login"
        assert cmd.description == "Log in to Claude Code"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = LoginCommand()
        assert "/login" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = LoginCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "Login"
        assert "onDone" in result.node["props"]
        assert "startingMessage" in result.node["props"]
