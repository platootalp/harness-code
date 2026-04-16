"""
Tests for commands/fast.py - Fast mode command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.fast import FastCommand
from claude_code.commands.base import CommandType


class TestFastCommand:
    """Tests for FastCommand."""

    def test_create(self) -> None:
        """Test creating FastCommand."""
        cmd = FastCommand()
        assert cmd.name == "fast"
        assert cmd.description == "Toggle fast mode (haiku model only)"
        assert cmd.argument_hint == "[on|off]"
        assert cmd.command_type == CommandType.LOCAL_JSX

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = FastCommand()
        assert "/fast" in cmd.get_help()
        assert "[on|off]" in cmd.get_help()

    def test_availability(self) -> None:
        """Test availability is set to claude-ai and console."""
        cmd = FastCommand()
        assert "claude-ai" in cmd.availability
        assert "console" in cmd.availability

    @pytest.mark.asyncio
    async def test_execute_on(self) -> None:
        """Test execute with 'on' argument."""
        cmd = FastCommand()
        result = await cmd.execute("on", {})

        assert result.type == "text"
        assert "Fast mode ON" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_off(self) -> None:
        """Test execute with 'off' argument."""
        cmd = FastCommand()
        result = await cmd.execute("off", {})

        assert result.type == "text"
        assert "Fast mode OFF" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_no_args_returns_jsx(self) -> None:
        """Test execute with no arguments returns JSX picker."""
        cmd = FastCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "FastModePicker"
