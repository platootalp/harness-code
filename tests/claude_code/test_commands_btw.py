"""
Tests for btw command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.btw import BtwCommand


class TestBtwCommand:
    """Tests for BtwCommand."""

    @pytest.mark.asyncio
    async def test_btw_no_question(self) -> None:
        """Test btw command with no question."""
        cmd = BtwCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "usage" in result.value.lower()

    @pytest.mark.asyncio
    async def test_btw_with_question(self) -> None:
        """Test btw command with a question."""
        cmd = BtwCommand()
        result = await cmd.execute(
            "What is Python?",
            {},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "What is Python?" in result.value
        assert "side question" in result.value.lower()
        assert "processed" in result.value.lower()

    @pytest.mark.asyncio
    async def test_btw_trims_whitespace(self) -> None:
        """Test btw command trims whitespace from question."""
        cmd = BtwCommand()
        result = await cmd.execute(
            "  Why is the sky blue?  ",
            {},
        )
        assert isinstance(result, CommandResult)
        assert "Why is the sky blue?" in result.value
        assert "  " not in result.value

    @pytest.mark.asyncio
    async def test_btw_preserves_context(self) -> None:
        """Test btw command mentions context preservation."""
        cmd = BtwCommand()
        result = await cmd.execute(
            "Quick question",
            {"messages": ["some context"]},
        )
        assert isinstance(result, CommandResult)
        assert "context" in result.value.lower()

    def test_btw_metadata(self) -> None:
        """Test btw command metadata."""
        cmd = BtwCommand()
        assert cmd.name == "btw"
        assert cmd.argument_hint == "<question>"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.immediate is True
        assert cmd.source == "builtin"

    def test_btw_get_help(self) -> None:
        """Test get_help() method."""
        cmd = BtwCommand()
        help_text = cmd.get_help()
        assert "/btw" in help_text
        assert "<question>" in help_text


class TestBtwCommandRegistry:
    """Tests for btw command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns btw command."""
        from claude_code.commands.btw import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "btw"
