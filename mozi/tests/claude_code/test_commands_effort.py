"""
Tests for commands/effort.py - Effort level command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.effort import EFFORT_LEVELS, EFFORT_DESCRIPTIONS, EffortCommand


class TestEffortCommand:
    """Tests for EffortCommand."""

    def test_create(self) -> None:
        """Test creating EffortCommand."""
        cmd = EffortCommand()
        assert cmd.name == "effort"
        assert cmd.description == "Set effort level for model usage"
        assert cmd.argument_hint == "[low|medium|high|max|auto]"
        assert cmd.immediate is True
        assert cmd.supports_non_interactive is True

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = EffortCommand()
        assert "/effort" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_no_args(self) -> None:
        """Test execute with no arguments shows current status."""
        cmd = EffortCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "Effort level: auto" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_current(self) -> None:
        """Test execute with 'current' argument."""
        cmd = EffortCommand()
        result = await cmd.execute("current", {})

        assert result.type == "text"
        assert "Effort level: auto" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_status(self) -> None:
        """Test execute with 'status' argument."""
        cmd = EffortCommand()
        result = await cmd.execute("status", {})

        assert result.type == "text"
        assert "Effort level: auto" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_help(self) -> None:
        """Test execute with help argument."""
        cmd = EffortCommand()
        result = await cmd.execute("--help", {})

        assert result.type == "text"
        assert "Usage:" in (result.value or "")
        assert "Effort levels" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_valid_levels(self) -> None:
        """Test execute with all valid effort levels."""
        cmd = EffortCommand()
        for level in EFFORT_LEVELS:
            if level == "auto":
                continue  # Skip auto since it doesn't have description
            result = await cmd.execute(level, {})
            assert result.type == "text"
            assert f"Set effort level to {level}" in (result.value or "")
            assert level in EFFORT_DESCRIPTIONS

    @pytest.mark.asyncio
    async def test_execute_invalid_level(self) -> None:
        """Test execute with invalid level."""
        cmd = EffortCommand()
        result = await cmd.execute("invalid", {})

        assert result.type == "text"
        assert "Invalid argument: invalid" in (result.value or "")
        assert "Valid options" in (result.value or "")

    @pytest.mark.asyncio
    async def test_effort_levels_complete(self) -> None:
        """Test that all expected effort levels are defined."""
        expected = {"low", "medium", "high", "max", "auto"}
        assert set(EFFORT_LEVELS) == expected
