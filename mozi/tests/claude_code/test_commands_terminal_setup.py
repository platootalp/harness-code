"""
Tests for commands/terminal_setup.py - Terminal Setup command.
"""

from __future__ import annotations

import os

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.terminal_setup import TerminalSetupCommand


class TestTerminalSetupCommand:
    """Tests for TerminalSetupCommand."""

    def test_create(self) -> None:
        """Test creating TerminalSetupCommand."""
        cmd = TerminalSetupCommand()
        assert cmd.name == "terminal-setup"
        # Description is dynamic based on terminal type
        assert cmd.description is not None
        assert len(cmd.description) > 0
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = TerminalSetupCommand()
        help_text = cmd.get_help()
        assert "terminal-setup" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text with setup instructions."""
        cmd = TerminalSetupCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        # Should have some terminal setup info
        assert len(result.value) > 0

    def test_native_terminals_defined(self) -> None:
        """Test native CSI u terminals are defined."""
        from claude_code.commands.terminal_setup import NATIVE_CSIU_TERMINALS

        assert "ghostty" in NATIVE_CSIU_TERMINALS
        assert "kitty" in NATIVE_CSIU_TERMINALS
        assert "iTerm.app" in NATIVE_CSIU_TERMINALS
        assert "WezTerm" in NATIVE_CSIU_TERMINALS
