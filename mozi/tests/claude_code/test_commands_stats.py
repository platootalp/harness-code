"""
Tests for commands/stats.py - Stats command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.stats import StatsCommand


class TestStatsCommand:
    """Tests for StatsCommand."""

    def test_create(self) -> None:
        """Test creating StatsCommand."""
        cmd = StatsCommand()
        assert cmd.name == "stats"
        assert cmd.description == "Show your Claude Code usage statistics and activity"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = StatsCommand()
        help_text = cmd.get_help()
        assert "/stats" in help_text

    def test_all_names(self) -> None:
        """Test _all_names."""
        cmd = StatsCommand()
        assert "stats" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node."""
        cmd = StatsCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "jsx"
        assert result.value is None
        assert result.node is not None
        assert result.node["type"] == "stats"

    @pytest.mark.asyncio
    async def test_execute_passes_context(self) -> None:
        """Test execute passes context in node."""
        cmd = StatsCommand()
        ctx = {"key": "value"}
        result = await cmd.execute("", ctx)
        assert result.node.get("context") == ctx

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that stats command ignores arguments."""
        cmd = StatsCommand()
        result = await cmd.execute("--verbose", {})
        assert result.type == "jsx"
