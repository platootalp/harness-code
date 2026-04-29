"""
Tests for commands/remote_env.py - Remote Environment command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.remote_env import RemoteEnvCommand


class TestRemoteEnvCommand:
    """Tests for RemoteEnvCommand."""

    def test_create(self) -> None:
        """Test creating RemoteEnvCommand."""
        cmd = RemoteEnvCommand()
        assert cmd.name == "remote-env"
        assert cmd.description == "Configure the default remote environment for teleport sessions"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = RemoteEnvCommand()
        help_text = cmd.get_help()
        assert "remote-env" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = RemoteEnvCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "remote-env"
