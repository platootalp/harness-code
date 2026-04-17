"""
Tests for commands/git.py - Git commands.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.git import (
    BranchCommand,
    CommitCommand,
    DiffCommand,
)

# =============================================================================
# CommitCommand Tests
# =============================================================================


class TestCommitCommand:
    """Tests for CommitCommand (Prompt type)."""

    def test_create(self) -> None:
        """Test creating CommitCommand."""
        cmd = CommitCommand()
        assert cmd.name == "commit"
        assert cmd.description == "Create a git commit"
        assert cmd.source == "builtin"
        assert cmd.command_type == CommandType.PROMPT

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = CommitCommand()
        assert "/commit" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_returns_prompt_content(self) -> None:
        """execute() should return content-type result with prompt."""
        cmd = CommitCommand()

        result = await cmd.execute("", {})

        assert result.type == "content"
        assert result.content is not None
        assert len(result.content) == 1
        assert result.content[0]["type"] == "text"
        text = result.content[0]["text"]
        assert "## Context" in text
        assert "## Git Safety Protocol" in text
        assert "## Your task" in text

    def test_prompt_includes_safety_protocol(self) -> None:
        """Generated prompt should include all safety rules."""
        cmd = CommitCommand()

        protocol = cmd._get_safety_protocol()

        assert "NEVER update the git config" in protocol
        assert "--no-verify" in protocol
        assert "--no-gpg-sign" in protocol
        assert "git commit --amend" in protocol
        assert "empty commit" in protocol
        assert "-i flag" in protocol  # Interactive commands banned

    @pytest.mark.asyncio
    async def test_prompt_includes_task_instructions(self) -> None:
        """Generated prompt should include task instructions."""
        cmd = CommitCommand()

        content = await cmd.get_prompt_content("", {})

        assert "Analyze all staged changes" in content
        assert "draft a commit message" in content

    @pytest.mark.asyncio
    async def test_prompt_includes_heredoc_syntax(self) -> None:
        """Generated prompt should include HEREDOC commit syntax."""
        cmd = CommitCommand()

        content = await cmd.get_prompt_content("", {})

        assert "HEREDOC syntax" in content
        assert "git commit -m" in content

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """execute() should handle args gracefully."""
        cmd = CommitCommand()

        result = await cmd.execute("some args", {})

        # Prompt commands ignore args
        assert result.type == "content"

    def test_run_git_success(self) -> None:
        """_run_git should return stdout on success."""
        cmd = CommitCommand()
        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout.strip.return_value = "M  file.py"
            mock_run.return_value = mock_result

            result = cmd._run_git(["git", "status"])

            assert result == "M  file.py"

    def test_run_git_timeout(self) -> None:
        """_run_git should return empty string on timeout."""
        cmd = CommitCommand()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 10)

            result = cmd._run_git(["git", "status"])

            assert result == ""

    def test_run_git_oserror(self) -> None:
        """_run_git should return empty string on OS error."""
        cmd = CommitCommand()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = OSError("git not found")

            result = cmd._run_git(["git", "status"])

            assert result == ""


# =============================================================================
# DiffCommand Tests
# =============================================================================


class TestDiffCommand:
    """Tests for DiffCommand (Local type)."""

    def test_create(self) -> None:
        """Test creating DiffCommand."""
        cmd = DiffCommand()
        assert cmd.name == "diff"
        assert cmd.description == "View uncommitted changes and per-turn diffs"
        assert cmd.source == "builtin"
        assert cmd.command_type == CommandType.LOCAL

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = DiffCommand()
        help_text = cmd.get_help()
        assert "/diff" in help_text

    @pytest.mark.asyncio
    async def test_execute_no_changes(self) -> None:
        """Test execute with no uncommitted changes."""
        cmd = DiffCommand()

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            result = await cmd.execute("", {})

            assert result.type == "text"
            assert "No changes" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_changes(self) -> None:
        """Test execute with uncommitted changes."""
        cmd = DiffCommand()
        diff_output = """diff --git a/file.py b/file.py
index abc..def 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 line one
-line two
+line two modified
+line three
"""

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = diff_output
            mock_run.return_value = mock_result

            result = await cmd.execute("", {})

            assert result.type == "text"
            assert "diff --git" in (result.value or "")
            call_args = mock_run.call_args[0][0]
            assert call_args == ["git", "diff"]

    @pytest.mark.asyncio
    async def test_execute_cached(self) -> None:
        """Test execute with --cached flag."""
        cmd = DiffCommand()

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "staged diff"
            mock_run.return_value = mock_result

            await cmd.execute("--cached", {})

            call_args = mock_run.call_args[0][0]
            assert "--cached" in call_args

    @pytest.mark.asyncio
    async def test_execute_with_path(self) -> None:
        """Test execute with file path."""
        cmd = DiffCommand()

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "diff for file.py"
            mock_run.return_value = mock_result

            await cmd.execute("file.py", {})

            call_args = mock_run.call_args[0][0]
            assert "file.py" in call_args

    @pytest.mark.asyncio
    async def test_execute_git_not_found(self) -> None:
        """Test execute when git is not found."""
        cmd = DiffCommand()

        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = await cmd.execute("", {})

            assert result.type == "text"
            assert "git not found" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        """Test execute with timeout."""
        cmd = DiffCommand()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git diff", 30)
            result = await cmd.execute("", {})

            assert result.type == "text"
            assert "timed out" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_error(self) -> None:
        """Test execute with exception."""
        cmd = DiffCommand()

        with patch("subprocess.run", side_effect=OSError("Permission denied")):
            result = await cmd.execute("", {})

            assert result.type == "text"
            assert "Error" in result.value


# =============================================================================
# BranchCommand Tests
# =============================================================================


class TestBranchCommand:
    """Tests for BranchCommand (Local type - conversation branching)."""

    def test_create(self) -> None:
        """Test creating BranchCommand."""
        cmd = BranchCommand()
        assert cmd.name == "branch"
        assert "Create a branch of the current conversation" in cmd.description
        assert cmd.source == "builtin"
        assert cmd.command_type == CommandType.LOCAL

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = BranchCommand()
        help_text = cmd.get_help()
        assert "/branch" in help_text

    def test_has_aliases_field(self) -> None:
        """BranchCommand should have aliases attribute."""
        cmd = BranchCommand()
        assert hasattr(cmd, "aliases")

    @pytest.mark.asyncio
    async def test_execute_no_repl_state(self) -> None:
        """execute without repl_state should return error."""
        cmd = BranchCommand()

        result = await cmd.execute("", {})

        assert result.type == "text"
        assert "No active session" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_with_title(self) -> None:
        """execute with custom title."""
        cmd = BranchCommand()

        result = await cmd.execute("my branch", {})

        # Without repl_state, should return error
        assert result.type == "text"
        assert "No active session" in (result.value or "")
