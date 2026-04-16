"""
Tests for resume command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.resume import ResumeCommand


class TestResumeCommand:
    """Tests for ResumeCommand."""

    @pytest.mark.asyncio
    async def test_resume_no_sessions(self) -> None:
        """Test resume with no session history."""
        cmd = ResumeCommand()
        result = await cmd.execute("", {})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "no previous conversations" in result.value.lower()

    @pytest.mark.asyncio
    async def test_resume_empty_sessions(self) -> None:
        """Test resume with empty session list."""
        cmd = ResumeCommand()
        result = await cmd.execute("", {"session_logs": []})
        assert isinstance(result, CommandResult)
        assert "no previous conversations" in result.value.lower()

    @pytest.mark.asyncio
    async def test_resume_with_sessions(self) -> None:
        """Test resume listing available sessions."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "abc-123",
                "title": "Test Session",
                "modified": "2024-01-01",
            },
        ]
        result = await cmd.execute("", {"session_logs": logs})
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "Test Session" in result.value
        assert "abc-123" in result.value

    @pytest.mark.asyncio
    async def test_resume_filter_current_session(self) -> None:
        """Test that current session is filtered from resume list."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "current-123",
                "title": "Current Session",
                "modified": "2024-01-01",
            },
            {
                "session_id": "other-456",
                "title": "Other Session",
                "modified": "2024-01-02",
            },
        ]
        result = await cmd.execute(
            "",
            {"session_id": "current-123", "session_logs": logs},
        )
        assert isinstance(result, CommandResult)
        assert "Current Session" not in result.value
        assert "Other Session" in result.value

    @pytest.mark.asyncio
    async def test_resume_by_uuid(self) -> None:
        """Test resume by session UUID."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Found Session",
                "modified": "2024-01-01",
            },
        ]
        result = await cmd.execute(
            "550e8400-e29b-41d4-a716-446655440000",
            {"session_logs": logs},
        )
        assert isinstance(result, CommandResult)
        assert result.type == "text"
        assert "Found Session" in result.value
        assert "550e8400-e29b-41d4-a716-446655440000" in result.value

    @pytest.mark.asyncio
    async def test_resume_uuid_not_found(self) -> None:
        """Test resume with non-existent UUID."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Existing Session",
                "modified": "2024-01-01",
            },
        ]
        result = await cmd.execute(
            "550e8400-e29b-41d4-a716-446655440001",
            {"session_logs": logs},
        )
        assert isinstance(result, CommandResult)
        assert "not found" in result.value.lower()

    @pytest.mark.asyncio
    async def test_resume_by_search_term(self) -> None:
        """Test resume by search term matching title."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "abc-123",
                "title": "Python bug fix",
                "first_prompt": "Fix the bug in main.py",
                "modified": "2024-01-01",
            },
        ]
        result = await cmd.execute("bug", {"session_logs": logs})
        assert isinstance(result, CommandResult)
        assert "Python bug fix" in result.value

    @pytest.mark.asyncio
    async def test_resume_multiple_matches(self) -> None:
        """Test resume with multiple title matches."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "abc-123",
                "title": "Bug fix - module A",
                "modified": "2024-01-01",
            },
            {
                "session_id": "def-456",
                "title": "Bug fix - module B",
                "modified": "2024-01-02",
            },
        ]
        result = await cmd.execute("Bug fix", {"session_logs": logs})
        assert isinstance(result, CommandResult)
        assert "2 sessions" in result.value.lower()

    @pytest.mark.asyncio
    async def test_resume_no_match(self) -> None:
        """Test resume with no matching sessions."""
        cmd = ResumeCommand()
        logs = [
            {
                "session_id": "abc-123",
                "title": "Python session",
                "modified": "2024-01-01",
            },
        ]
        result = await cmd.execute("javascript", {"session_logs": logs})
        assert isinstance(result, CommandResult)
        assert "no sessions found" in result.value.lower()

    def test_resume_metadata(self) -> None:
        """Test resume command metadata."""
        cmd = ResumeCommand()
        assert cmd.name == "resume"
        assert "continue" in cmd.aliases
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"

    def test_resume_get_help(self) -> None:
        """Test get_help() method."""
        cmd = ResumeCommand()
        help_text = cmd.get_help()
        assert "/resume" in help_text
        assert "conversation" in help_text.lower()


class TestResumeCommandRegistry:
    """Tests for resume command registry functions."""

    def test_get_all_commands(self) -> None:
        """Test get_all_commands returns resume command."""
        from claude_code.commands.resume import get_all_commands

        commands = get_all_commands()
        assert isinstance(commands, list)
        assert len(commands) == 1
        assert commands[0].name == "resume"
