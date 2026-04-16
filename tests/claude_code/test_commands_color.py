"""
Tests for commands/color.py - Color command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.color import ColorCommand
from claude_code.commands.base import CommandType


class TestColorCommand:
    """Tests for ColorCommand."""

    def test_create(self) -> None:
        """Test creating ColorCommand."""
        cmd = ColorCommand()
        assert cmd.name == "color"
        assert cmd.description == "Set the prompt bar color for this session"
        assert cmd.argument_hint == "<color|default>"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.immediate is True
        assert cmd.supports_non_interactive is True

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = ColorCommand()
        assert "/color" in cmd.get_help()
        assert "<color|default>" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_no_args(self) -> None:
        """Test execute with no arguments."""
        cmd = ColorCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "Please provide a color" in (result.value or "")
        assert "Available colors" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_valid_color(self) -> None:
        """Test execute with a valid color."""
        cmd = ColorCommand()
        result = await cmd.execute("blue", {})

        assert result.type == "text"
        assert "Session color set to: blue" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_invalid_color(self) -> None:
        """Test execute with an invalid color."""
        cmd = ColorCommand()
        result = await cmd.execute("invalid_color", {})

        assert result.type == "text"
        assert 'Invalid color "invalid_color"' in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_reset_aliases(self) -> None:
        """Test execute with reset aliases."""
        cmd = ColorCommand()
        for alias in ["default", "reset", "none", "gray", "grey"]:
            result = await cmd.execute(alias, {})
            assert result.type == "text"
            assert "reset to default" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_color_case_insensitive(self) -> None:
        """Test execute with uppercase color."""
        cmd = ColorCommand()
        result = await cmd.execute("BLUE", {})

        assert result.type == "text"
        assert "Session color set to: blue" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_context(self) -> None:
        """Test execute passes context without error."""
        cmd = ColorCommand()
        result = await cmd.execute("red", {"user": "test"})

        assert result.type == "text"
        assert "Session color set to: red" in (result.value or "")
