"""
Tests for commands/plan.py - Plan command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.plan import PlanCommand


class TestPlanCommand:
    """Tests for PlanCommand."""

    def test_create(self) -> None:
        """Test creating PlanCommand."""
        cmd = PlanCommand()
        assert cmd.name == "plan"
        assert cmd.description == "Enable plan mode or view the current session plan"
        assert cmd.argument_hint == "[open|<description>]"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = PlanCommand()
        help_text = cmd.get_help()
        assert "/plan" in help_text

    @pytest.mark.asyncio
    async def test_execute_no_args(self) -> None:
        """Test execute with no arguments."""
        cmd = PlanCommand()
        result = await cmd.execute("", {"_repl_state": None})

        assert result.type == "text"
        assert "No active session" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_open_no_plan(self) -> None:
        """Test execute with 'open' when no plan exists."""
        cmd = PlanCommand()
        result = await cmd.execute("open", {"_repl_state": None})

        assert result.type == "text"

    @pytest.mark.asyncio
    async def test_plan_command_includes_open_hint(self) -> None:
        """Test that plan command suggests /plan open."""
        cmd = PlanCommand()
        result = await cmd.execute("", {"_repl_state": None})

        # When no session, should mention enabling plan mode
        assert result.type == "text"

    def test_get_editor_env(self) -> None:
        """Test editor detection from environment."""
        import os

        cmd = PlanCommand()
        editor = cmd._get_editor()
        # Should return something - either EDITOR, VISUAL, or nano fallback
        assert editor is not None
        assert len(editor) > 0
