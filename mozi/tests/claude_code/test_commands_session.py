"""
Tests for session command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.session import SessionCommand


class TestSessionCommand:
    """Tests for SessionCommand."""

    @pytest.mark.asyncio
    async def test_session_without_remote_url(self) -> None:
        """Test session command when not in remote mode."""
        cmd = SessionCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "remote mode" in result.value.lower()

    @pytest.mark.asyncio
    async def test_session_with_remote_url(self) -> None:
        """Test session command with remote URL."""
        cmd = SessionCommand()
        result = await cmd.execute(
            "",
            {"_remote_session_url": "https://claude.ai/session/abc123"},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "https://claude.ai/session/abc123" in result.value
        assert "browser" in result.value.lower()

    @pytest.mark.asyncio
    async def test_session_alias_remote(self) -> None:
        """Test that 'remote' is an alias for 'session'."""
        cmd = SessionCommand()
        assert "session" in cmd._all_names
        assert "remote" in cmd._all_names
        assert cmd.name == "session"

    def test_session_metadata(self) -> None:
        """Test session command metadata."""
        cmd = SessionCommand()
        assert cmd.name == "session"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_session_get_help(self) -> None:
        """Test get_help() method."""
        cmd = SessionCommand()
        help_text = cmd.get_help()
        assert "/session" in help_text
        assert "remote" in help_text.lower()


class TestSessionCommandRegistry:
    """Tests for session command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns session command."""
        from claude_code.commands.session import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "session"
