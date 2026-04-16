"""
Tests for commands/exit.py - Exit command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.exit import ExitCommand


class MockREPLState:
    """Mock REPLState for testing."""

    def __init__(self) -> None:
        self.exit_requested = False
        self.running = True


class TestExitCommand:
    """Tests for ExitCommand."""

    def test_create(self) -> None:
        """Test creating ExitCommand."""
        cmd = ExitCommand()
        assert cmd.name == "exit"
        assert "quit" in cmd.aliases
        assert "q" in cmd.aliases
        assert cmd.description == "Exit Claude Code"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.immediate is True
        assert cmd.supports_non_interactive is True
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = ExitCommand()
        help_text = cmd.get_help()
        assert "/exit" in help_text

    def test_all_names_includes_aliases(self) -> None:
        """Test that _all_names includes name and aliases."""
        cmd = ExitCommand()
        assert "exit" in cmd._all_names
        assert "quit" in cmd._all_names
        assert "q" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_basic(self) -> None:
        """Test basic exit execution."""
        cmd = ExitCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert result.value is not None
        assert "Goodbye" in result.value

    @pytest.mark.asyncio
    async def test_execute_with_repl_state(self) -> None:
        """Test exit execution with repl_state."""
        cmd = ExitCommand()
        state = MockREPLState()

        result = await cmd.execute("", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert result.type == "text"

    @pytest.mark.asyncio
    async def test_execute_with_worktree_session(self) -> None:
        """Test exit execution with worktree session doesn't crash."""
        cmd = ExitCommand()
        state = MockREPLState()
        state._worktree_session = True  # type: ignore[attr-defined]

        # Should not raise
        result = await cmd.execute("", {"_repl_state": state})
        assert result.type == "text"

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that exit ignores arguments."""
        cmd = ExitCommand()
        result = await cmd.execute("force", {})
        assert result.type == "text"
        assert result.value is not None
        assert "Goodbye" in result.value
