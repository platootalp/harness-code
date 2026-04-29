"""
Tests for commands/tag.py - Tag command.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.tag import TagCommand


class TestTagCommand:
    """Tests for TagCommand."""

    def test_create(self) -> None:
        """Test creating TagCommand."""
        cmd = TagCommand()
        assert cmd.name == "tag"
        assert cmd.description == "Toggle a searchable tag on the current session"
        assert cmd.argument_hint == "<tag-name>"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = TagCommand()
        help_text = cmd.get_help()
        assert "/tag" in help_text
        assert "toggle" in help_text.lower()

    @pytest.mark.asyncio
    async def test_execute_no_args_shows_help(self) -> None:
        """Test execute with no arguments shows help."""
        cmd = TagCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "/tag" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_help_flag_shows_help(self) -> None:
        """Test execute with --help shows help."""
        cmd = TagCommand()
        for flag in ["--help", "-h", "help"]:
            result = await cmd.execute(flag, {})
            assert result.type == "text"
            assert "/tag" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_empty_tag_name(self) -> None:
        """Test execute with empty/whitespace tag name shows help."""
        cmd = TagCommand()
        result = await cmd.execute("   ", {})

        assert result.type == "text"
        # Whitespace-only args show help text
        assert "/tag" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_no_session(self) -> None:
        """Test execute with no session returns error."""
        cmd = TagCommand()
        result = await cmd.execute("test-tag", {"_repl_state": None})

        assert result.type == "text"
        assert "No active session" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_leading_hash(self) -> None:
        """Test execute handles leading hash from tag."""
        cmd = TagCommand()
        # Mock repl_state
        mock_session = type("MockSession", (), {"session_id": "test-session-123"})()
        mock_state = type("MockState", (), {"session": mock_session})()

        with tempfile.TemporaryDirectory() as tmpdir:
            tags_file = Path(tmpdir) / "session-tags.jsonl"
            # Patch the tags file path
            original_tags_file = cmd._get_tags_file
            cmd._get_tags_file = lambda: tags_file

            try:
                result = await cmd.execute("#test-tag", {"_repl_state": mock_state})
                assert result.type == "text"
                # Tag is saved without # prefix internally
                # but displayed with # in the message
                assert "test-tag" in (result.value or "")
            finally:
                cmd._get_tags_file = original_tags_file

    def test_get_tags_file(self) -> None:
        """Test tags file location."""
        cmd = TagCommand()
        tags_file = cmd._get_tags_file()
        assert tags_file is not None
        assert tags_file.name == "session-tags.jsonl"
