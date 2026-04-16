"""
Tests for commands/sandbox_toggle.py - Sandbox Toggle command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.sandbox_toggle import SandboxToggleCommand


class TestSandboxToggleCommand:
    """Tests for SandboxToggleCommand."""

    def test_create(self) -> None:
        """Test creating SandboxToggleCommand."""
        cmd = SandboxToggleCommand()
        assert cmd.name == "sandbox"
        assert cmd.argument_hint == 'exclude "command pattern"'
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.immediate is True
        assert cmd.source == "builtin"
        # Description is dynamic, just check it exists
        assert cmd.description is not None

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = SandboxToggleCommand()
        help_text = cmd.get_help()
        assert "sandbox" in help_text

    def test_check_dependencies(self) -> None:
        """Test dependency checking."""
        cmd = SandboxToggleCommand()
        deps = cmd._check_dependencies()
        # Should return a bool
        assert isinstance(deps, bool)

    @pytest.mark.asyncio
    async def test_execute_no_args_shows_status(self) -> None:
        """Test execute with no arguments shows status."""
        cmd = SandboxToggleCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None

    @pytest.mark.asyncio
    async def test_execute_exclude_empty_pattern(self) -> None:
        """Test execute with exclude but empty pattern."""
        cmd = SandboxToggleCommand()
        result = await cmd.execute("exclude", {})

        assert result.type == "text"
        assert "Error" in (result.value or "") or "please" in (result.value or "").lower()

    @pytest.mark.asyncio
    async def test_execute_unknown_subcommand(self) -> None:
        """Test execute with unknown subcommand."""
        cmd = SandboxToggleCommand()
        result = await cmd.execute("unknown-cmd", {})

        assert result.type == "text"
        assert "Unknown subcommand" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_exclude_with_pattern(self) -> None:
        """Test execute with exclude and pattern."""
        cmd = SandboxToggleCommand()
        result = await cmd.execute('exclude "npm run test"', {})

        assert result.type == "text"
        # Either adds the pattern or errors gracefully
        assert result.value is not None
