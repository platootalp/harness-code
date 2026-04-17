"""
Tests for context command.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.context import ContextCommand


class MockContentBlock:
    """Mock content block."""

    def __init__(self, text: str = "") -> None:
        self.text = text


class MockMessage:
    """Mock message."""

    def __init__(self, role: str, text: str = "") -> None:
        self.role = MagicMock()
        self.role.value = role
        self.content_blocks = [MockContentBlock(text)]


class TestContextCommand:
    """Tests for ContextCommand."""

    @pytest.mark.asyncio
    async def test_context_empty_messages(self) -> None:
        """Test context command with no messages."""
        cmd = ContextCommand()
        result = await cmd.execute("", {"messages": []})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "Context Usage" in result.value

    @pytest.mark.asyncio
    async def test_context_with_messages(self) -> None:
        """Test context command with messages."""
        cmd = ContextCommand()
        messages = [
            MockMessage("user", "Hello world this is a test message"),
            MockMessage("assistant", "Hi there!"),
        ]

        result = await cmd.execute(
            "",
            {"messages": messages, "model": "claude-sonnet-4-20250514"},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "claude-sonnet-4-20250514" in result.value
        assert "Messages" in result.value

    @pytest.mark.asyncio
    async def test_context_with_mcp_tools(self) -> None:
        """Test context command includes MCP tools."""
        cmd = ContextCommand()

        # Create mock MCP tools
        tool1 = MagicMock()
        tool1.name = "filesystem_read"
        tool1.server = "local-server"

        result = await cmd.execute(
            "",
            {"messages": [], "mcp_tools": [tool1]},
        )
        assert isinstance(result, CommandResult)
        assert "MCP Tools" in result.value
        assert "filesystem_read" in result.value
        assert "local-server" in result.value

    @pytest.mark.asyncio
    async def test_context_with_skills(self) -> None:
        """Test context command includes active skills."""
        cmd = ContextCommand()

        skill = MagicMock()
        skill.name = "refactor"
        skill.description = "Refactor code"

        result = await cmd.execute(
            "",
            {"messages": [], "active_skills": [skill]},
        )
        assert isinstance(result, CommandResult)
        assert "Active Skills" in result.value
        assert "refactor" in result.value

    @pytest.mark.asyncio
    async def test_context_with_memory_files(self) -> None:
        """Test context command includes memory files."""
        cmd = ContextCommand()

        result = await cmd.execute(
            "",
            {"messages": [], "memory_files": ["/path/to/memory.md"]},
        )
        assert isinstance(result, CommandResult)
        assert "Memory Files" in result.value
        assert "/path/to/memory.md" in result.value

    @pytest.mark.asyncio
    async def test_context_shows_token_breakdown(self) -> None:
        """Test context command shows token breakdown."""
        cmd = ContextCommand()
        messages = [
            MockMessage("user", "A" * 1000),
            MockMessage("assistant", "B" * 500),
        ]

        result = await cmd.execute(
            "",
            {"messages": messages, "model": "test-model"},
        )
        assert isinstance(result, CommandResult)
        assert "tokens" in result.value.lower()
        assert "percentage" in result.value.lower()

    @pytest.mark.asyncio
    async def test_context_calculates_categories(self) -> None:
        """Test that context calculates category breakdowns."""
        cmd = ContextCommand()
        messages = [MockMessage("user", "Test content")]

        result = await cmd.execute(
            "",
            {"messages": messages},
        )
        assert isinstance(result, CommandResult)
        # Should have category table
        assert "Category" in result.value

    def test_context_metadata(self) -> None:
        """Test context command metadata."""
        cmd = ContextCommand()
        assert cmd.name == "context"
        assert cmd.description == "Show context usage information"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.supports_non_interactive is True
        assert cmd.source == "builtin"

    def test_context_get_help(self) -> None:
        """Test get_help() method."""
        cmd = ContextCommand()
        help_text = cmd.get_help()
        assert "/context" in help_text


class TestContextCommandRegistry:
    """Tests for context command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns context command."""
        from claude_code.commands.context import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "context"
