"""
Tests for commands/chrome.py - Chrome command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.chrome import ChromeCommand


class TestChromeCommand:
    """Tests for ChromeCommand."""

    def test_create(self) -> None:
        """Test creating ChromeCommand."""
        cmd = ChromeCommand()
        assert cmd.name == "chrome"
        assert cmd.description == "Claude in Chrome (Beta) settings"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = ChromeCommand()
        help_text = cmd.get_help()
        assert "chrome" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text with chrome info."""
        cmd = ChromeCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "Chrome" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_mentions_features(self) -> None:
        """Test execute mentions Chrome features."""
        cmd = ChromeCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        text = result.value or ""
        assert "setup" in text.lower() or "download" in text.lower()
