"""
Tests for core builtin commands.
"""

from __future__ import annotations

import pytest
from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.clear import (
    ClearCommand,
    CompactCommand,
    HelpCommand,
    ModelCommand,
    get_all_commands,
)


class MockREPLState:
    """Mock REPLState for testing."""

    def __init__(self) -> None:
        self.messages = []
        self.command_history = []
        self.history_index = -1
        self.is_compressing = False

        class Session:
            model = "claude-sonnet-4-20250514"
        self.session = Session()


class TestClearCommand:
    """Tests for ClearCommand."""

    @pytest.mark.asyncio
    async def test_clear_conversation(self) -> None:
        """Test clearing conversation messages."""
        cmd = ClearCommand()
        state = MockREPLState()
        state.messages = [{"role": "user", "content": "hello"}]

        result = await cmd.execute("", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "cleared" in result.value.lower()
        assert len(state.messages) == 0

    @pytest.mark.asyncio
    async def test_clear_with_history_flag(self) -> None:
        """Test clearing with --history flag."""
        cmd = ClearCommand()
        state = MockREPLState()
        state.messages = [{"role": "user", "content": "hello"}]
        state.command_history = ["ls", "cd /tmp"]
        state.history_index = 2

        result = await cmd.execute("--history", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert "history" in result.value.lower()
        assert len(state.command_history) == 0
        assert state.history_index == -1

    @pytest.mark.asyncio
    async def test_clear_without_state(self) -> None:
        """Test clear works even without repl_state."""
        cmd = ClearCommand()
        result = await cmd.execute("", {})
        assert result.type == "text"
        assert "cleared" in result.value.lower()


class TestCompactCommand:
    """Tests for CompactCommand."""

    @pytest.mark.asyncio
    async def test_compact_sets_state(self) -> None:
        """Test that compact sets is_compressing flag."""
        cmd = CompactCommand()
        state = MockREPLState()

        result = await cmd.execute("", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "compaction" in result.value.lower()
        assert state.is_compressing is True

    @pytest.mark.asyncio
    async def test_compact_without_state(self) -> None:
        """Test compact works without repl_state."""
        cmd = CompactCommand()
        result = await cmd.execute("", {})
        assert result.type == "text"


class TestHelpCommand:
    """Tests for HelpCommand."""

    @pytest.mark.asyncio
    async def test_help_general(self) -> None:
        """Test general help output."""
        cmd = HelpCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "Available commands" in result.value
        assert "/clear" in result.value
        assert "/compact" in result.value
        assert "/help" in result.value
        assert "/model" in result.value

    @pytest.mark.asyncio
    async def test_help_specific_command(self) -> None:
        """Test help for a specific command."""
        cmd = HelpCommand()
        result = await cmd.execute("clear", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "/clear" in result.value

    @pytest.mark.asyncio
    async def test_help_unknown_command(self) -> None:
        """Test help for unknown command."""
        cmd = HelpCommand()
        result = await cmd.execute("nonexistent", {})
        assert isinstance(result, CommandResult)
        assert "Unknown command" in result.value

    @pytest.mark.asyncio
    async def test_help_with_registry(self) -> None:
        """Test help with command registry."""
        cmd = HelpCommand(get_all_commands=get_all_commands)
        result = await cmd.execute("clear", {})
        assert "/clear" in result.value
        assert "conversation" in result.value.lower()

    def test_get_help(self) -> None:
        """Test get_help() method."""
        cmd = HelpCommand()
        help_text = cmd.get_help()
        assert "/help" in help_text


class TestModelCommand:
    """Tests for ModelCommand."""

    @pytest.mark.asyncio
    async def test_model_show_current(self) -> None:
        """Test showing current model."""
        cmd = ModelCommand()
        state = MockREPLState()

        result = await cmd.execute("", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "claude-sonnet" in result.value.lower()

    @pytest.mark.asyncio
    async def test_model_change(self) -> None:
        """Test changing to a different model."""
        cmd = ModelCommand()
        state = MockREPLState()

        result = await cmd.execute("claude-opus-4-5", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "changed" in result.value.lower()
        assert state.session.model == "claude-opus-4-5"

    @pytest.mark.asyncio
    async def test_model_invalid(self) -> None:
        """Test setting an invalid model."""
        cmd = ModelCommand()
        state = MockREPLState()

        result = await cmd.execute("invalid-model-xyz", {"_repl_state": state})
        assert isinstance(result, CommandResult)
        assert "Unknown model" in result.value

    @pytest.mark.asyncio
    async def test_model_without_state(self) -> None:
        """Test model command without repl_state."""
        cmd = ModelCommand()
        result = await cmd.execute("", {})
        assert result.type == "text"
        assert "unknown" in result.value.lower()

    @pytest.mark.asyncio
    async def test_model_all_available(self) -> None:
        """Test that all models in AVAILABLE_MODELS work."""
        cmd = ModelCommand()
        state = MockREPLState()
        for model in cmd.AVAILABLE_MODELS:
            result = await cmd.execute(model, {"_repl_state": state})
            assert "changed" in result.value.lower()
            assert state.session.model == model


class TestGetAllCommands:
    """Tests for command registry functions."""

    def test_get_all_commands_returns_list(self) -> None:
        """Test that get_all_commands returns a list."""
        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 4

    def test_all_core_commands_present(self) -> None:
        """Test all core commands are present."""
        commands = get_all_commands()
        names = {cmd.name for cmd in commands}
        assert names == {"clear", "compact", "help", "model"}

    def test_command_types(self) -> None:
        """Test command types are correct."""
        commands = get_all_commands()
        for cmd in commands:
            assert cmd.command_type == CommandType.LOCAL

    def test_help_is_recursive(self) -> None:
        """Test that HelpCommand references itself for listing."""
        commands = get_all_commands()
        help_cmd = next(c for c in commands if c.name == "help")
        # The help command has a reference to get_all_commands
        assert help_cmd._get_all_commands is get_all_commands


class TestCommandMetadata:
    """Tests for command metadata."""

    def test_clear_metadata(self) -> None:
        """Test ClearCommand metadata."""
        cmd = ClearCommand()
        assert cmd.name == "clear"
        assert cmd.supports_non_interactive is True

    def test_compact_metadata(self) -> None:
        """Test CompactCommand metadata."""
        cmd = CompactCommand()
        assert cmd.name == "compact"
        assert cmd.supports_non_interactive is True

    def test_help_metadata(self) -> None:
        """Test HelpCommand metadata."""
        cmd = HelpCommand()
        assert cmd.name == "help"
        assert cmd.argument_hint == "[command]"

    def test_model_metadata(self) -> None:
        """Test ModelCommand metadata."""
        cmd = ModelCommand()
        assert cmd.name == "model"
        assert cmd.argument_hint == "[model-name]"
