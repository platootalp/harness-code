"""
Tests for commands/hooks.py - Hooks command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.hooks import HooksCommand
from claude_code.commands.base import CommandType


class TestHooksCommand:
    """Tests for HooksCommand."""

    def test_create(self) -> None:
        """Test creating HooksCommand."""
        cmd = HooksCommand()
        assert cmd.name == "hooks"
        assert cmd.description == "View hook configurations for tool events"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.immediate is True
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = HooksCommand()
        assert "/hooks" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = HooksCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "HooksConfigMenu"
        assert "toolNames" in result.node["props"]
        assert "onExit" in result.node["props"]
