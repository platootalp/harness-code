"""
Tests for commands/advisor.py - Advisor command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.advisor import AdvisorCommand
from claude_code.commands.base import CommandType


class TestAdvisorCommand:
    """Tests for AdvisorCommand (stub implementation)."""

    def test_create(self) -> None:
        """Test creating AdvisorCommand."""
        cmd = AdvisorCommand()
        assert cmd.name == "advisor"
        assert cmd.description == "Ask the advisor for suggestions"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = AdvisorCommand()
        assert "/advisor" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = AdvisorCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "AdvisorPanel"
        assert "onDone" in result.node["props"]
