"""
Tests for rename command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.rename import RenameCommand


class MockSession:
    """Mock session object."""

    def __init__(self) -> None:
        self.name: str | None = None
        self.metadata: dict = {}


class MockREPLState:
    """Mock REPL state."""

    def __init__(self) -> None:
        self.session = MockSession()
        self.session_name: str | None = None


class TestRenameCommand:
    """Tests for RenameCommand."""

    @pytest.mark.asyncio
    async def test_rename_with_name(self) -> None:
        """Test renaming with a provided name."""
        cmd = RenameCommand()
        state = MockREPLState()

        result = await cmd.execute(
            "My Custom Session",
            {"_repl_state": state, "_is_teammate": False},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "My Custom Session" in result.value
        assert state.session_name == "My Custom Session"

    @pytest.mark.asyncio
    async def test_rename_with_whitespace(self) -> None:
        """Test renaming with extra whitespace."""
        cmd = RenameCommand()
        state = MockREPLState()

        result = await cmd.execute(
            "  Session With Spaces  ",
            {"_repl_state": state},
        )
        assert isinstance(result, CommandResult)
        assert "Session With Spaces" in result.value

    @pytest.mark.asyncio
    async def test_rename_empty_generates_name(self) -> None:
        """Test rename with no args generates name from context."""
        cmd = RenameCommand()

        # Mock message with user role
        class MockContentBlock:
            def __init__(self) -> None:
                self.text = "Fix the login bug in auth.py"

        class MockMessage:
            def __init__(self) -> None:
                self.role = type("Role", (), {"value": "user"})()
                self.content_blocks = [MockContentBlock()]

            def get(self, key: str, default: str = "") -> str:
                if key == "role":
                    return self.role.value
                return default

        result = await cmd.execute(
            "",
            {"messages": [MockMessage()], "_is_teammate": False},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        # Should generate name from first user message
        assert "Fix the login bug" in result.value

    @pytest.mark.asyncio
    async def test_rename_no_context(self) -> None:
        """Test rename with no args and no context."""
        cmd = RenameCommand()

        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert "could not generate" in result.value.lower()

    @pytest.mark.asyncio
    async def test_rename_empty_messages(self) -> None:
        """Test rename with empty messages list."""
        cmd = RenameCommand()

        result = await cmd.execute("", {"messages": []})
        assert isinstance(result, CommandResult)
        assert "could not generate" in result.value.lower()

    @pytest.mark.asyncio
    async def test_rename_teammate_blocked(self) -> None:
        """Test that teammates cannot rename."""
        cmd = RenameCommand()

        result = await cmd.execute(
            "New Name",
            {"_is_teammate": True},
        )
        assert isinstance(result, CommandResult)
        assert "teammate" in result.value.lower()
        assert "cannot rename" in result.value.lower()

    def test_rename_metadata(self) -> None:
        """Test rename command metadata."""
        cmd = RenameCommand()
        assert cmd.name == "rename"
        assert cmd.argument_hint == "[name]"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.immediate is True
        assert cmd.source == "builtin"

    def test_rename_get_help(self) -> None:
        """Test get_help() method."""
        cmd = RenameCommand()
        help_text = cmd.get_help()
        assert "/rename" in help_text


class TestRenameCommandRegistry:
    """Tests for rename command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns rename command."""
        from claude_code.commands.rename import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "rename"
