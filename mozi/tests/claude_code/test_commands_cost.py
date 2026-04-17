"""
Tests for commands/cost.py - Cost command.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.cost import CostCommand, _is_claude_ai_subscriber


class TestIsClaudeAiSubscriber:
    """Tests for _is_claude_ai_subscriber helper."""

    def test_subscriber(self) -> None:
        """Test subscriber detection."""
        original = os.environ.get("CLAUDE_AI_SUBSCRIBER")
        try:
            os.environ["CLAUDE_AI_SUBSCRIBER"] = "1"
            from claude_code.commands.cost import _is_claude_ai_subscriber as check
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
            from claude_code.commands.cost import _is_claude_ai_subscriber as check
            assert check() is False
        finally:
            if original is not None:
                os.environ["CLAUDE_AI_SUBSCRIBER"] = original


class TestCostCommand:
    """Tests for CostCommand."""

    def test_create(self) -> None:
        """Test creating CostCommand."""
        cmd = CostCommand()
        assert cmd.name == "cost"
        assert cmd.description == "Show the total cost and duration of the current session"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.supports_non_interactive is True
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = CostCommand()
        help_text = cmd.get_help()
        assert "/cost" in help_text

    def test_all_names(self) -> None:
        """Test _all_names."""
        cmd = CostCommand()
        assert "cost" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_no_cost_state(self) -> None:
        """Test execute without cost state."""
        cmd = CostCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert result.value is not None
        assert "not available" in result.value

    @pytest.mark.asyncio
    async def test_execute_with_cost_state(self) -> None:
        """Test execute with cost state."""
        cmd = CostCommand()
        cost_state = {
            "total_cost": 0.1234,
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "is_using_overage": False,
        }
        result = await cmd.execute("", {"_cost_state": cost_state, "_is_claude_ai_subscriber": False})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert result.value is not None
        assert "0.1234" in result.value
        assert "1,000" in result.value
        assert "500" in result.value

    @pytest.mark.asyncio
    async def test_execute_subscriber_no_overage(self) -> None:
        """Test subscriber execution without overage."""
        cmd = CostCommand()
        cost_state = {"total_cost": 0.0, "total_input_tokens": 0, "total_output_tokens": 0, "is_using_overage": False}
        result = await cmd.execute("", {"_cost_state": cost_state, "_is_claude_ai_subscriber": True, "_user_type": "user"})
        assert isinstance(result, CommandResult)
        assert result.value is not None
        assert "subscription" in result.value

    @pytest.mark.asyncio
    async def test_execute_subscriber_with_overage(self) -> None:
        """Test subscriber execution with overage."""
        cmd = CostCommand()
        cost_state = {"total_cost": 0.0, "total_input_tokens": 0, "total_output_tokens": 0, "is_using_overage": True}
        result = await cmd.execute("", {"_cost_state": cost_state, "_is_claude_ai_subscriber": True, "_user_type": "user"})
        assert isinstance(result, CommandResult)
        assert result.value is not None
        assert "overage" in result.value

    @pytest.mark.asyncio
    async def test_format_cost_includes_ant_only(self) -> None:
        """Test ANT users see cost info even when subscribed."""
        cmd = CostCommand()
        cost_state = {"total_cost": 1.5, "total_input_tokens": 5000, "total_output_tokens": 2000, "is_using_overage": False}
        result = await cmd.execute("", {"_cost_state": cost_state, "_is_claude_ai_subscriber": True, "_user_type": "ant"})
        assert isinstance(result, CommandResult)
        assert result.value is not None
        assert "ANT-ONLY" in result.value
        assert "1.5000" in result.value

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that cost command ignores arguments."""
        cmd = CostCommand()
        result = await cmd.execute("--verbose", {"_cost_state": {}})
        assert result.type == "text"
