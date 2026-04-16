"""
Tests for commands/theme.py - Theme command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.theme import ThemeCommand
from claude_code.commands.base import CommandType


class TestThemeCommand:
    """Tests for ThemeCommand."""

    def test_create(self) -> None:
        """Test creating ThemeCommand."""
        cmd = ThemeCommand()
        assert cmd.name == "theme"
        assert cmd.description == "Change the theme"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = ThemeCommand()
        assert "/theme" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = ThemeCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "ThemePicker"
        assert "onThemeSelect" in result.node["props"]
        assert "onCancel" in result.node["props"]

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """Test execute with args still returns JSX."""
        cmd = ThemeCommand()
        result = await cmd.execute("some-arg", {})

        assert result.type == "jsx"
        assert result.node["type"] == "ThemePicker"
