"""
Tests for commands/commit.py - Git commit command.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_code.commands.commit import CommitCommand


class TestCommitCommand:
    """Tests for CommitCommand."""

    def test_name(self) -> None:
        assert CommitCommand().name == "commit"

    def test_description(self) -> None:
        assert "git commit" in CommitCommand().description.lower()

    def test_argument_hint(self) -> None:
        assert CommitCommand().argument_hint is None

    def test_source(self) -> None:
        assert CommitCommand().source == "builtin"

    def test_is_prompt_command(self) -> None:
        """CommitCommand is a PromptCommand."""
        from claude_code.commands.base import CommandType

        cmd = CommitCommand()
        assert cmd.command_type == CommandType.PROMPT

    def test_allowed_tools(self) -> None:
        """CommitCommand has allowed tools list."""
        cmd = CommitCommand()
        assert len(cmd._allowed_tools) > 0
        assert any("git add" in t for t in cmd._allowed_tools)
        assert any("git status" in t for t in cmd._allowed_tools)
        assert any("git commit" in t for t in cmd._allowed_tools)

    def test_get_help(self) -> None:
        cmd = CommitCommand()
        assert "/commit" in cmd.get_help()
        assert "git commit" in cmd.get_help()

    def test_progress_message(self) -> None:
        cmd = CommitCommand()
        assert "commit" in cmd._progress_message.lower()

    @pytest.mark.asyncio
    async def test_get_prompt_content_includes_context(self) -> None:
        """get_prompt_content generates prompt with git context."""
        cmd = CommitCommand()

        content = await cmd.get_prompt_content("", {})

        assert "## Context" in content
        assert "## Git Safety Protocol" in content
        assert "## Your task" in content
        assert "git commit" in content.lower()
        assert "staged changes" in content.lower()

    @pytest.mark.asyncio
    async def test_get_prompt_content_includes_safety_protocol(self) -> None:
        """get_prompt_content includes safety protocol."""
        cmd = CommitCommand()

        content = await cmd.get_prompt_content("", {})

        assert "NEVER update the git config" in content
        assert "ALWAYS create NEW commits" in content
        assert "Never use git commands with the -i flag" in content

    @pytest.mark.asyncio
    async def test_get_prompt_content_includes_git_context(self) -> None:
        """get_prompt_content includes git context."""
        cmd = CommitCommand()

        content = await cmd.get_prompt_content("", {})

        assert "Current git status" in content or "git repository" in content
        assert "Recent commits" in content or "git repository" in content

    @pytest.mark.asyncio
    async def test_execute_returns_content_type(self) -> None:
        """execute returns content-type CommandResult."""
        cmd = CommitCommand()

        result = await cmd.execute("", {})

        assert result.type == "content"
        assert result.content is not None
        assert len(result.content) > 0
        assert result.content[0]["type"] == "text"

    def test_run_git_returns_stdout(self) -> None:
        """_run_git returns command output."""
        cmd = CommitCommand()

        # git --version should always succeed
        output = cmd._run_git(["git", "--version"])
        assert "git" in output.lower()

    def test_run_git_handles_error(self) -> None:
        """_run_git returns empty string on error."""
        cmd = CommitCommand()

        # Non-existent command should return empty
        output = cmd._run_git(["nonexistent_command_xyz"])
        assert output == ""

    def test_run_git_timeout(self) -> None:
        """_run_git returns empty string on timeout."""
        import subprocess

        cmd = CommitCommand()

        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("cmd", 1)):
            output = cmd._run_git(["git", "status"])
            assert output == ""

    def test_get_git_context_no_repo(self) -> None:
        """_get_git_context handles non-git directory."""
        cmd = CommitCommand()

        # In a non-git directory, status would fail
        context = cmd._get_git_context()
        assert isinstance(context, str)
