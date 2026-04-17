"""
Tests for commands/passes.py - Guest passes command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.passes import PassesCommand
from claude_code.commands.base import CommandType


class TestPassesCommand:
    """Tests for PassesCommand."""

    def test_create(self) -> None:
        """Test creating PassesCommand."""
        cmd = PassesCommand()
        assert cmd.name == "passes"
        assert cmd.description == "Show guest passes"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = PassesCommand()
        assert "/passes" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = PassesCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "Passes"
        assert "onDone" in result.node["props"]
