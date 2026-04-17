"""
Tests for commands/rewind.py - Rewind command.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.rewind import RewindCommand


class TestRewindCommand:
    """Tests for RewindCommand."""

    def test_create(self) -> None:
        """Test creating RewindCommand."""
        cmd = RewindCommand()
        assert cmd.name == "rewind"
        assert "checkpoint" in cmd.aliases
        assert cmd.description == "Rewind to a previous checkpoint in the conversation"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.supports_non_interactive is False
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = RewindCommand()
        help_text = cmd.get_help()
        assert "/rewind" in help_text

    def test_all_names(self) -> None:
        """Test _all_names includes aliases."""
        cmd = RewindCommand()
        assert "rewind" in cmd._all_names
        assert "checkpoint" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_returns_skip(self) -> None:
        """Test that execute returns skip type."""
        cmd = RewindCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "skip"
        assert result.value is None

    @pytest.mark.asyncio
    async def test_execute_calls_open_selector(self) -> None:
        """Test that execute calls openMessageSelector if provided."""
        cmd = RewindCommand()
        mock_selector = Mock()

        result = await cmd.execute("", {"openMessageSelector": mock_selector})
        assert result.type == "skip"
        mock_selector.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_handles_non_callable(self) -> None:
        """Test that execute handles non-callable openMessageSelector."""
        cmd = RewindCommand()
        result = await cmd.execute("", {"openMessageSelector": "not a function"})
        assert result.type == "skip"

    @pytest.mark.asyncio
    async def test_execute_handles_missing_selector(self) -> None:
        """Test that execute works without openMessageSelector."""
        cmd = RewindCommand()
        result = await cmd.execute("", {})
        assert result.type == "skip"

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that rewind command ignores arguments."""
        cmd = RewindCommand()
        result = await cmd.execute("checkpoint-id-123", {})
        assert result.type == "skip"
