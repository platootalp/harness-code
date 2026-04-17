"""
Tests for commands in clear.py - Clear, Compact, Help, and Model commands.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from claude_code.commands.clear import (
    ClearCommand,
    CompactCommand,
    HelpCommand,
    ModelCommand,
    get_all_commands,
)


class TestClearCommand:
    """Tests for ClearCommand."""

    def test_name(self) -> None:
        assert ClearCommand().name == "clear"

    def test_description(self) -> None:
        assert "clear" in ClearCommand().description.lower()

    def test_argument_hint(self) -> None:
        assert "--history" in ClearCommand().argument_hint

    def test_supports_non_interactive(self) -> None:
        assert ClearCommand().supports_non_interactive is True

    def test_execute_clears_messages(self) -> None:
        """ClearCommand clears messages from repl_state."""
        messages = [{"role": "user", "content": "hello"}]
        repl_state = MagicMock()
        repl_state.messages = messages
        repl_state.command_history = []
        repl_state.history_index = -1

        context = {"_repl_state": repl_state}
        cmd = ClearCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", context))

        assert result.type == "text"
        assert "Conversation cleared" in result.value
        assert len(repl_state.messages) == 0

    def test_execute_clears_history_flag(self) -> None:
        """ClearCommand with --history flag clears command history."""
        repl_state = MagicMock()
        repl_state.messages = [{"role": "user", "content": "hello"}]
        repl_state.command_history = ["cmd1", "cmd2"]
        repl_state.history_index = 2

        context = {"_repl_state": repl_state}
        cmd = ClearCommand()

        import asyncio

        result = asyncio.run(cmd.execute("--history", context))

        assert "Command history also cleared" in result.value
        assert len(repl_state.command_history) == 0
        assert repl_state.history_index == -1

    def test_execute_without_repl_state(self) -> None:
        """ClearCommand works without repl_state in context."""
        cmd = ClearCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", {}))

        assert result.type == "text"
        assert "Conversation cleared" in result.value

    def test_get_help(self) -> None:
        assert "/clear" in ClearCommand().get_help()


class TestCompactCommand:
    """Tests for CompactCommand."""

    def test_name(self) -> None:
        assert CompactCommand().name == "compact"

    def test_description(self) -> None:
        assert "compress" in CompactCommand().description.lower()

    def test_supports_non_interactive(self) -> None:
        assert CompactCommand().supports_non_interactive is True

    def test_execute_sets_compressing(self) -> None:
        """CompactCommand sets is_compressing on repl_state."""
        repl_state = MagicMock()
        repl_state.is_compressing = False

        context = {"_repl_state": repl_state}
        cmd = CompactCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", context))

        assert result.type == "text"
        assert "compaction" in result.value.lower()
        assert repl_state.is_compressing is True

    def test_execute_without_repl_state(self) -> None:
        """CompactCommand works without repl_state in context."""
        cmd = CompactCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", {}))

        assert result.type == "text"
        assert "compaction" in result.value.lower()

    def test_get_help(self) -> None:
        assert "/compact" in CompactCommand().get_help()


class TestHelpCommand:
    """Tests for HelpCommand."""

    def test_name(self) -> None:
        assert HelpCommand().name == "help"

    def test_description(self) -> None:
        assert "help" in HelpCommand().description.lower()

    def test_argument_hint(self) -> None:
        assert "[command]" in HelpCommand().argument_hint

    def test_supports_non_interactive(self) -> None:
        assert HelpCommand().supports_non_interactive is True

    def test_execute_without_args_lists_commands(self) -> None:
        """HelpCommand without args shows command list."""
        cmd = HelpCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", {}))

        assert result.type == "text"
        assert "Available commands" in result.value
        assert "/clear" in result.value
        assert "/compact" in result.value
        assert "/help" in result.value
        assert "/model" in result.value

    def test_execute_with_command_name(self) -> None:
        """HelpCommand with command name shows specific help."""
        cmd = HelpCommand()

        import asyncio

        result = asyncio.run(cmd.execute("clear", {}))

        assert result.type == "text"
        assert "/clear" in result.value

    def test_execute_unknown_command(self) -> None:
        """HelpCommand with unknown command returns error."""
        cmd = HelpCommand()

        import asyncio

        result = asyncio.run(cmd.execute("nonexistent", {}))

        assert result.type == "text"
        assert "Unknown command" in result.value

    def test_execute_with_registry(self) -> None:
        """HelpCommand uses registry for command-specific help."""
        all_cmds = get_all_commands()
        cmd = HelpCommand(get_all_commands=lambda: all_cmds)

        import asyncio

        result = asyncio.run(cmd.execute("clear", {}))

        assert result.type == "text"
        assert "/clear" in result.value
        assert "clear" in result.value.lower()

    def test_get_help(self) -> None:
        assert "/help" in HelpCommand().get_help()


class TestModelCommand:
    """Tests for ModelCommand."""

    def test_name(self) -> None:
        assert ModelCommand().name == "model"

    def test_description(self) -> None:
        assert "model" in ModelCommand().description.lower()

    def test_argument_hint(self) -> None:
        assert "[model-name]" in ModelCommand().argument_hint

    def test_supports_non_interactive(self) -> None:
        assert ModelCommand().supports_non_interactive is True

    def test_available_models(self) -> None:
        """ModelCommand has available models list."""
        cmd = ModelCommand()
        assert len(cmd.AVAILABLE_MODELS) > 0
        assert "claude-opus-4-5" in cmd.AVAILABLE_MODELS

    def test_execute_shows_current_model(self) -> None:
        """ModelCommand without args shows current model."""
        session = MagicMock()
        session.model = "claude-opus-4-5"
        repl_state = MagicMock()
        repl_state.session = session

        context = {"_repl_state": repl_state}
        cmd = ModelCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", context))

        assert result.type == "text"
        assert "claude-opus-4-5" in result.value

    def test_execute_without_repl_state(self) -> None:
        """ModelCommand without repl_state shows unknown model."""
        cmd = ModelCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", {}))

        assert result.type == "text"
        assert "unknown" in result.value

    def test_execute_changes_model(self) -> None:
        """ModelCommand with valid model name changes the model."""
        session = MagicMock()
        session.model = "claude-opus-4-5"
        repl_state = MagicMock()
        repl_state.session = session

        context = {"_repl_state": repl_state}
        cmd = ModelCommand()

        import asyncio

        result = asyncio.run(cmd.execute("claude-sonnet-4-7", context))

        assert result.type == "text"
        assert "claude-sonnet-4-7" in result.value
        assert repl_state.session.model == "claude-sonnet-4-7"

    def test_execute_unknown_model(self) -> None:
        """ModelCommand with unknown model returns error."""
        repl_state = MagicMock()
        repl_state.session = MagicMock()

        context = {"_repl_state": repl_state}
        cmd = ModelCommand()

        import asyncio

        result = asyncio.run(cmd.execute("invalid-model", context))

        assert result.type == "text"
        assert "Unknown model" in result.value
        assert "invalid-model" in result.value

    def test_get_help(self) -> None:
        assert "/model" in ModelCommand().get_help()


class TestGetAllCommands:
    """Tests for command registry functions."""

    def test_get_all_commands_returns_list(self) -> None:
        """get_all_commands returns a list of commands."""
        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 4

    def test_all_commands_have_names(self) -> None:
        """All commands in registry have names."""
        commands = get_all_commands()
        for cmd in commands:
            assert cmd.name
            assert len(cmd.name) > 0

    def test_all_commands_have_descriptions(self) -> None:
        """All commands in registry have descriptions."""
        commands = get_all_commands()
        for cmd in commands:
            assert cmd.description
            assert len(cmd.description) > 0
