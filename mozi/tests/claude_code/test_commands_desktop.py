"""
Tests for commands/desktop.py - Desktop command.
"""

from __future__ import annotations

import platform

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.desktop import DesktopCommand


class TestDesktopCommand:
    """Tests for DesktopCommand."""

    def test_create(self) -> None:
        """Test creating DesktopCommand."""
        cmd = DesktopCommand()
        assert cmd.name == "desktop"
        assert cmd.aliases == ["app"]
        assert cmd.description == "Continue the current session in Claude Desktop"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = DesktopCommand()
        help_text = cmd.get_help()
        assert "desktop" in help_text

    def test_is_supported_platform(self) -> None:
        """Test platform support check."""
        cmd = DesktopCommand()
        result = cmd._is_supported_platform()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text with desktop info."""
        cmd = DesktopCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "Desktop" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_mentions_download(self) -> None:
        """Test execute mentions download link."""
        cmd = DesktopCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        text = result.value or ""
        assert "download" in text.lower() or "claude.ai" in text.lower()

    def test_aliases(self) -> None:
        """Test command aliases."""
        cmd = DesktopCommand()
        assert "app" in cmd.aliases
        assert "app" in cmd._all_names
