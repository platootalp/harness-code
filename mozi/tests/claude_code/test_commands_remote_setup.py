"""
Tests for commands/remote_setup.py - Remote Setup command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.remote_setup import RemoteSetupCommand


class TestRemoteSetupCommand:
    """Tests for RemoteSetupCommand."""

    def test_create(self) -> None:
        """Test creating RemoteSetupCommand."""
        cmd = RemoteSetupCommand()
        assert cmd.name == "remote-setup"
        assert cmd.description == "Setup Claude Code on the web (requires connecting your GitHub account)"
        assert cmd.argument_hint is None
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = RemoteSetupCommand()
        help_text = cmd.get_help()
        assert "remote-setup" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = RemoteSetupCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "remote-setup"
