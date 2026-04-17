"""
Tests for commands/output_style.py - Output Style command (deprecated).
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.output_style import OutputStyleCommand


class TestOutputStyleCommand:
    """Tests for OutputStyleCommand."""

    def test_create(self) -> None:
        """Test creating OutputStyleCommand."""
        cmd = OutputStyleCommand()
        assert cmd.name == "output-style"
        assert cmd.description == "Deprecated: use /config to change output style"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.is_hidden is True
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = OutputStyleCommand()
        help_text = cmd.get_help()
        assert "/output-style" in help_text
        assert "deprecated" in help_text.lower()

    @pytest.mark.asyncio
    async def test_execute_returns_deprecation_notice(self) -> None:
        """Test execute returns deprecation notice."""
        cmd = OutputStyleCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "/config" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """Test execute with arguments."""
        cmd = OutputStyleCommand()
        result = await cmd.execute("some-arg", {})

        assert result.type == "text"
        assert "/config" in (result.value or "")
