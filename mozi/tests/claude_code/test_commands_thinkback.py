"""
Tests for commands/thinkback.py - Thinkback command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.thinkback import ThinkbackCommand


class TestThinkbackCommand:
    """Tests for ThinkbackCommand."""

    def test_create(self) -> None:
        """Test creating ThinkbackCommand."""
        cmd = ThinkbackCommand()
        assert cmd.name == "think-back"
        assert cmd.description == "Your 2025 Claude Code Year in Review"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = ThinkbackCommand()
        help_text = cmd.get_help()
        assert "think-back" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text result."""
        cmd = ThinkbackCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "2025" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """Test execute with arguments (ignored)."""
        cmd = ThinkbackCommand()
        result = await cmd.execute("some-arg", {})

        assert result.type == "text"
        assert "2025" in (result.value or "")
