"""
Tests for commands/usage.py - Usage command.
"""

from __future__ import annotations

import os

import pytest

from claude_code.commands.base import Availability, CommandResult, CommandType
from claude_code.commands.usage import UsageCommand, _is_claude_ai_subscriber


class TestIsClaudeAiSubscriber:
    """Tests for _is_claude_ai_subscriber helper."""

    def test_subscriber(self) -> None:
        """Test subscriber detection."""
        original = os.environ.get("CLAUDE_AI_SUBSCRIBER")
        try:
            os.environ["CLAUDE_AI_SUBSCRIBER"] = "1"
            from claude_code.commands.usage import _is_claude_ai_subscriber as check
            assert check() is True
        finally:
            if original is None:
                os.environ.pop("CLAUDE_AI_SUBSCRIBER", None)
            else:
                os.environ["CLAUDE_AI_SUBSCRIBER"] = original

    def test_non_subscriber(self) -> None:
        """Test non-subscriber detection."""
        original = os.environ.get("CLAUDE_AI_SUBSCRIBER")
        try:
            os.environ.pop("CLAUDE_AI_SUBSCRIBER", None)
            from claude_code.commands.usage import _is_claude_ai_subscriber as check
            assert check() is False
        finally:
            if original is not None:
                os.environ["CLAUDE_AI_SUBSCRIBER"] = original


class TestUsageCommand:
    """Tests for UsageCommand."""

    def test_create(self) -> None:
        """Test creating UsageCommand."""
        cmd = UsageCommand()
        assert cmd.name == "usage"
        assert cmd.description == "Show plan usage limits"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert Availability.CLAUDE_AI.value in cmd.availability
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = UsageCommand()
        help_text = cmd.get_help()
        assert "/usage" in help_text

    def test_all_names(self) -> None:
        """Test _all_names."""
        cmd = UsageCommand()
        assert "usage" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node."""
        cmd = UsageCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "jsx"
        assert result.value is None
        assert result.node is not None
        assert result.node["type"] == "settings"
        assert result.node["default_tab"] == "Usage"

    @pytest.mark.asyncio
    async def test_execute_passes_context(self) -> None:
        """Test execute passes context in node."""
        cmd = UsageCommand()
        ctx = {"key": "value"}
        result = await cmd.execute("", ctx)
        assert result.node.get("context") == ctx

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that usage command ignores arguments."""
        cmd = UsageCommand()
        result = await cmd.execute("--verbose", {})
        assert result.type == "jsx"
