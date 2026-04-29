"""
Tests for commands/vim.py - Vim command.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.vim import VimCommand


class TestVimCommand:
    """Tests for VimCommand."""

    def test_create(self) -> None:
        """Test creating VimCommand."""
        cmd = VimCommand()
        assert cmd.name == "vim"
        assert cmd.description == "Toggle between Vim and Normal editing modes"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.supports_non_interactive is False
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = VimCommand()
        help_text = cmd.get_help()
        assert "/vim" in help_text

    @pytest.mark.asyncio
    async def test_execute_normal_to_vim(self) -> None:
        """Test toggling from normal to vim mode."""
        cmd = VimCommand()
        mock_set_config = MagicMock()
        result = await cmd.execute("", {"_config": {}, "_set_config": mock_set_config})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert result.value is not None
        assert "vim" in result.value
        assert "set to vim" in result.value

    @pytest.mark.asyncio
    async def test_execute_vim_to_normal(self) -> None:
        """Test toggling from vim to normal mode."""
        cmd = VimCommand()
        mock_set_config = MagicMock()
        result = await cmd.execute("", {"_config": {"editorMode": "vim"}, "_set_config": mock_set_config})
        assert isinstance(result, CommandResult)
        assert result.value is not None
        assert "normal" in result.value

    @pytest.mark.asyncio
    async def test_execute_emacs_falls_back_to_normal(self) -> None:
        """Test that emacs mode falls back to normal."""
        cmd = VimCommand()
        mock_set_config = MagicMock()
        result = await cmd.execute("", {"_config": {"editorMode": "emacs"}, "_set_config": mock_set_config})
        assert isinstance(result, CommandResult)
        # emacs -> normal -> vim toggle should result in vim mode
        assert result.value is not None
        assert "vim" in result.value

    @pytest.mark.asyncio
    async def test_execute_without_config(self) -> None:
        """Test execute without config context."""
        cmd = VimCommand()
        result = await cmd.execute("", {})
        assert result.type == "text"
        # Default is normal, so toggling gives vim
        assert result.value is not None
        assert "vim" in result.value

    @pytest.mark.asyncio
    async def test_execute_ignores_args(self) -> None:
        """Test that vim command ignores arguments."""
        cmd = VimCommand()
        result = await cmd.execute("--force", {})
        assert result.type == "text"
