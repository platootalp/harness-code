"""
Tests for commands/logout.py - Logout command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.logout import LogoutCommand
from claude_code.commands.base import CommandType


class TestLogoutCommand:
    """Tests for LogoutCommand."""

    def test_create(self) -> None:
        """Test creating LogoutCommand."""
        cmd = LogoutCommand()
        assert cmd.name == "logout"
        assert cmd.description == "Log out from Claude Code"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = LogoutCommand()
        assert "/logout" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = LogoutCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "Logout"
        assert "onDone" in result.node["props"]
        assert result.node["props"]["performLogout"] is True
