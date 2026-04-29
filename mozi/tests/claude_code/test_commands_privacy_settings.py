"""
Tests for commands/privacy_settings.py - Privacy Settings command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.privacy_settings import PrivacySettingsCommand


class TestPrivacySettingsCommand:
    """Tests for PrivacySettingsCommand."""

    def test_create(self) -> None:
        """Test creating PrivacySettingsCommand."""
        cmd = PrivacySettingsCommand()
        assert cmd.name == "privacy-settings"
        assert cmd.description == "View and update your privacy settings"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = PrivacySettingsCommand()
        help_text = cmd.get_help()
        assert "privacy-settings" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = PrivacySettingsCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "privacy-settings"
