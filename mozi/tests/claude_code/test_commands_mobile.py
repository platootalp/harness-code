"""
Tests for commands/mobile.py - Mobile command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.mobile import MobileCommand


class TestMobileCommand:
    """Tests for MobileCommand."""

    def test_create(self) -> None:
        """Test creating MobileCommand."""
        cmd = MobileCommand()
        assert cmd.name == "mobile"
        assert cmd.aliases == ["ios", "android"]
        assert cmd.description == "Show QR code to download the Claude mobile app"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = MobileCommand()
        help_text = cmd.get_help()
        assert "mobile" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text with mobile app info."""
        cmd = MobileCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "mobile" in (result.value or "").lower()
        assert "iOS" in (result.value or "") or "Apple" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_mentions_app_stores(self) -> None:
        """Test execute mentions app store URLs."""
        cmd = MobileCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        text = result.value or ""
        assert "apps.apple.com" in text or "play.google.com" in text

    def test_aliases(self) -> None:
        """Test command aliases."""
        cmd = MobileCommand()
        assert "ios" in cmd.aliases
        assert "android" in cmd.aliases
        assert "ios" in cmd._all_names
        assert "android" in cmd._all_names
