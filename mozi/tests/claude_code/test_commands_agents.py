"""
Tests for agents command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.agents import AgentsCommand
from claude_code.commands.base import CommandResult, CommandType


class MockREPLState:
    """Mock REPL state."""

    def __init__(self, model_name: str = "claude-sonnet-4-20250514") -> None:
        class Session:
            pass
        self.session = Session()
        self.session.model = model_name


class TestAgentsCommand:
    """Tests for AgentsCommand."""

    @pytest.mark.asyncio
    async def test_agents_no_definitions(self) -> None:
        """Test agents command with no agent definitions."""
        cmd = AgentsCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        # Should show built-in agents even without custom definitions
        assert "default" in result.value
        assert "coder" in result.value
        assert "Built-in Agents" in result.value

    @pytest.mark.asyncio
    async def test_agents_with_definitions(self) -> None:
        """Test agents command displays built-in agents."""
        cmd = AgentsCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        # Should show built-in agents
        assert "default" in result.value
        assert "coder" in result.value
        assert "reviewer" in result.value
        assert "architect" in result.value

    @pytest.mark.asyncio
    async def test_agents_shows_current_agent(self) -> None:
        """Test agents command shows current agent."""
        cmd = AgentsCommand()
        result = await cmd.execute(
            "",
            {"current_agent": "coder"},
        )
        assert isinstance(result, CommandResult)
        assert "Current agent: coder" in result.value
        assert "*" in result.value  # Current agent marker

    @pytest.mark.asyncio
    async def test_agents_shows_model(self) -> None:
        """Test agents command shows current model."""
        cmd = AgentsCommand()
        state = MockREPLState("claude-opus-4-5")

        result = await cmd.execute(
            "",
            {"_repl_state": state},
        )
        assert isinstance(result, CommandResult)
        assert "claude-opus-4-5" in result.value

    @pytest.mark.asyncio
    async def test_agents_groups_by_source(self) -> None:
        """Test that agents are grouped by source."""
        cmd = AgentsCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert "Built-in Agents" in result.value

    @pytest.mark.asyncio
    async def test_agents_with_custom_definitions(self) -> None:
        """Test agents command with custom agent definitions."""
        cmd = AgentsCommand()
        custom_agents = [
            {
                "name": "custom-agent",
                "description": "My custom agent",
                "source": "projectSettings",
            },
        ]

        result = await cmd.execute(
            "",
            {"agent_definitions": custom_agents},
        )
        assert isinstance(result, CommandResult)
        assert "custom-agent" in result.value
        assert "My custom agent" in result.value

    def test_agents_metadata(self) -> None:
        """Test agents command metadata."""
        cmd = AgentsCommand()
        assert cmd.name == "agents"
        assert cmd.argument_hint == "[agent-name]"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_agents_get_help(self) -> None:
        """Test get_help() method."""
        cmd = AgentsCommand()
        help_text = cmd.get_help()
        assert "/agents" in help_text


class TestAgentsCommandRegistry:
    """Tests for agents command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns agents command."""
        from claude_code.commands.agents import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "agents"
