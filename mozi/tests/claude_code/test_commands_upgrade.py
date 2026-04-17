"""
Tests for commands/upgrade.py - Upgrade command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.upgrade import UpgradeCommand
from claude_code.commands.base import CommandType


class TestUpgradeCommand:
    """Tests for UpgradeCommand."""

    def test_create(self) -> None:
        """Test creating UpgradeCommand."""
        cmd = UpgradeCommand()
        assert cmd.name == "upgrade"
        assert cmd.description == "Upgrade to Max plan"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.supports_non_interactive is False

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = UpgradeCommand()
        assert "/upgrade" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = UpgradeCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "Upgrade"
        assert "onDone" in result.node["props"]
        assert "url" in result.node["props"]
        assert "claude.ai/upgrade/max" in result.node["props"]["url"]
