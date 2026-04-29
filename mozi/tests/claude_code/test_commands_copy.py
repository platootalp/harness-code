"""
Tests for copy command.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.copy import CopyCommand


class TestCopyCommand:
    """Tests for CopyCommand."""

    @pytest.mark.asyncio
    async def test_copy_no_messages(self) -> None:
        """Test copy command with no messages."""
        cmd = CopyCommand()
        result = await cmd.execute("", {"messages": []})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "no assistant response" in result.value.lower()

    @pytest.mark.asyncio
    async def test_copy_with_clipboard(self) -> None:
        """Test copy command with working clipboard."""
        cmd = CopyCommand()
        clipboard_calls: list[str] = []

        def mock_clipboard(text: str) -> None:
            clipboard_calls.append(text)

        # Mock messages with dict-style access
        messages = [
            MagicMock(),
            MagicMock(),
        ]
        messages[0].get.side_effect = lambda key, default="", **kw: {
            "role": "user",
            "content": "First response",
        }.get(key, default)
        messages[1].get.side_effect = lambda key, default="", **kw: {
            "role": "assistant",
            "content": [{"type": "text", "text": "Second response"}],
        }.get(key, default)

        result = await cmd.execute(
            "",
            {"messages": messages, "_clipboard": mock_clipboard},
        )
        assert isinstance(result, CommandResult)
        # Should work with dict-based messages too

    @pytest.mark.asyncio
    async def test_copy_invalid_index(self) -> None:
        """Test copy command with invalid index."""
        cmd = CopyCommand()
        messages = [MagicMock()]
        messages[0].get.side_effect = lambda key, default="", **kw: {
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
        }.get(key, default)

        result = await cmd.execute(
            "abc",
            {"messages": messages},
        )
        assert isinstance(result, CommandResult)
        # Should handle gracefully

    @pytest.mark.asyncio
    async def test_copy_index_out_of_range(self) -> None:
        """Test copy command with out of range index."""
        cmd = CopyCommand()
        messages = [MagicMock()]
        messages[0].get.side_effect = lambda key, default="", **kw: {
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
        }.get(key, default)

        result = await cmd.execute(
            "999",
            {"messages": messages},
        )
        assert isinstance(result, CommandResult)
        assert "invalid" in result.value.lower() or "only" in result.value.lower()

    def test_copy_metadata(self) -> None:
        """Test copy command metadata."""
        cmd = CopyCommand()
        assert cmd.name == "copy"
        assert "copy" in cmd.description.lower()
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_copy_get_help(self) -> None:
        """Test get_help() method."""
        cmd = CopyCommand()
        help_text = cmd.get_help()
        assert "/copy" in help_text


class TestCopyCommandRegistry:
    """Tests for copy command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns copy command."""
        from claude_code.commands.copy import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "copy"
