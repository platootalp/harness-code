"""
Tests for commands/status.py - Status command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.status import StatusCommand


class TestStatusCommand:
    """Tests for StatusCommand."""

    def test_create(self) -> None:
        """Test creating StatusCommand."""
        cmd = StatusCommand()
        assert cmd.name == "status"
        assert "version" in cmd.description.lower()
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.immediate is True
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = StatusCommand()
        help_text = cmd.get_help()
        assert "/status" in help_text

    def test_all_names(self) -> None:
        """Test _all_names."""
        cmd = StatusCommand()
        assert "status" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node."""
        cmd = StatusCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "jsx"
        assert result.value is None
        assert result.node is not None
        assert result.node["type"] == "settings"
        assert result.node["default_tab"] == "Status"

    @pytest.mark.asyncio
    async def test_execute_passes_context(self) -> None:
        """Test execute passes context in node."""
        cmd = StatusCommand()
        ctx = {"key": "value"}
        result = await cmd.execute("", ctx)
        assert result.node.get("context") == ctx

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that status command ignores arguments."""
        cmd = StatusCommand()
        result = await cmd.execute("--verbose", {})
        assert result.type == "jsx"
