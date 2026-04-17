"""
Tests for commands/branch.py - Branch command.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_code.commands.branch import (
    BranchCommand,
    derive_first_prompt,
    get_unique_fork_name,
)


class TestDeriveFirstPrompt:
    """Tests for derive_first_prompt helper."""

    def test_none_input(self) -> None:
        assert derive_first_prompt(None) == "Branched conversation"

    def test_empty_dict(self) -> None:
        assert derive_first_prompt({}) == "Branched conversation"

    def test_no_message_key(self) -> None:
        assert derive_first_prompt({"foo": "bar"}) == "Branched conversation"

    def test_string_content(self) -> None:
        msg = {"message": {"content": "Fix the login bug"}}
        assert derive_first_prompt(msg) == "Fix the login bug"

    def test_list_content_with_text(self) -> None:
        msg = {"message": {"content": [{"type": "text", "text": "Hello world"}]}}
        assert derive_first_prompt(msg) == "Hello world"

    def test_list_content_no_text(self) -> None:
        msg = {"message": {"content": [{"type": "image", "data": "..."}]}}
        assert derive_first_prompt(msg) == "Branched conversation"

    def test_truncates_long_content(self) -> None:
        long_text = "x" * 200
        result = derive_first_prompt({"message": {"content": long_text}})
        assert len(result) == 100
        assert result == "x" * 100

    def test_collapses_whitespace(self) -> None:
        msg = {"message": {"content": "Hello   \n\n  world  "}}
        assert derive_first_prompt(msg) == "Hello world"


class TestGetUniqueForkName:
    """Tests for get_unique_fork_name helper."""

    def test_basic_name(self) -> None:
        """Returns base name with (Branch) when no collision."""
        result = get_unique_fork_name("My task")
        assert result == "My task (Branch)"

    def test_no_sessions_dir(self) -> None:
        """Returns base name when sessions dir doesn't exist."""
        from pathlib import Path

        with patch.object(Path, "is_dir", return_value=False):
            result = get_unique_fork_name("My task")
            assert result == "My task (Branch)"


class TestBranchCommand:
    """Tests for BranchCommand."""

    def test_name(self) -> None:
        assert BranchCommand().name == "branch"

    def test_description(self) -> None:
        assert "branch" in BranchCommand().description.lower()
        assert "conversation" in BranchCommand().description.lower()

    def test_argument_hint(self) -> None:
        assert "[name]" in BranchCommand().argument_hint

    def test_aliases(self) -> None:
        assert BranchCommand().aliases == []

    def test_source(self) -> None:
        assert BranchCommand().source == "builtin"

    def test_get_help(self) -> None:
        assert "/branch" in BranchCommand().get_help()

    def test_all_names_includes_name(self) -> None:
        cmd = BranchCommand()
        assert "branch" in cmd._all_names

    @pytest.mark.asyncio
    async def test_execute_without_repl_state(self) -> None:
        """execute returns error without repl_state."""
        cmd = BranchCommand()

        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "Error" in result.value
        assert "No active session" in result.value

    @pytest.mark.asyncio
    async def test_execute_without_session(self) -> None:
        """execute returns error without session."""
        repl_state = MagicMock(spec=[])
        repl_state.session = None

        cmd = BranchCommand()

        result = await cmd.execute("", {"_repl_state": repl_state})

        assert result.type == "text"
        assert "Error" in result.value

    @pytest.mark.asyncio
    async def test_execute_creates_fork(self) -> None:
        """execute creates a fork and returns branch message."""
        repl_state = MagicMock()
        repl_state.session = MagicMock()
        repl_state.session.session_id = "original-session-123"
        repl_state.messages = []

        cmd = BranchCommand()

        # Mock _save_fork_metadata to prevent actual file I/O
        with patch.object(cmd, "_save_fork_metadata"):
            result = await cmd.execute("", {"_repl_state": repl_state})

        assert result.type == "text"
        assert "Branched" in result.value
        assert "original-session-123" in result.value

    @pytest.mark.asyncio
    async def test_execute_with_custom_title(self) -> None:
        """execute uses custom title when provided."""
        repl_state = MagicMock()
        repl_state.session = MagicMock()
        repl_state.session.session_id = "original-123"
        repl_state.messages = []

        cmd = BranchCommand()

        with patch.object(cmd, "_save_fork_metadata"):
            result = await cmd.execute("My feature branch", {"_repl_state": repl_state})

        assert "My feature branch" in result.value
        assert "Branched" in result.value

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self) -> None:
        """execute returns error message on exception."""
        repl_state = MagicMock()
        repl_state.session = MagicMock()
        repl_state.session.session_id = "sess"
        repl_state.messages = []

        with patch.object(
            BranchCommand, "_save_fork_metadata", side_effect=Exception("disk error")
        ):
            cmd = BranchCommand()

            result = await cmd.execute("", {"_repl_state": repl_state})

            assert result.type == "text"
            assert "Failed to branch" in result.value
