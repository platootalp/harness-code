"""
Tests for commands/extra_usage.py - Extra Usage command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.extra_usage import ExtraUsageCommand


class TestExtraUsageCommand:
    """Tests for ExtraUsageCommand."""

    def test_create(self) -> None:
        """Test creating ExtraUsageCommand."""
        cmd = ExtraUsageCommand()
        assert cmd.name == "extra-usage"
        assert cmd.description == "Configure extra usage to keep working when limits are hit"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = ExtraUsageCommand()
        help_text = cmd.get_help()
        assert "extra-usage" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text with usage info."""
        cmd = ExtraUsageCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "usage" in (result.value or "").lower()
        assert "claude.ai" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """Test execute with arguments."""
        cmd = ExtraUsageCommand()
        result = await cmd.execute("some-arg", {})

        assert result.type == "text"
        assert "usage" in (result.value or "").lower()
