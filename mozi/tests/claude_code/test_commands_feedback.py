"""
Tests for commands/feedback.py - Feedback command.
"""

from __future__ import annotations

import pytest

# Import directly from command module to avoid __init__.py rewind.py bug
from claude_code.commands.feedback import FeedbackCommand
from claude_code.commands.base import CommandType


class TestFeedbackCommand:
    """Tests for FeedbackCommand."""

    def test_create(self) -> None:
        """Test creating FeedbackCommand."""
        cmd = FeedbackCommand()
        assert cmd.name == "feedback"
        assert "bug" in cmd.aliases
        assert cmd.description == "Submit feedback or report a bug"
        assert cmd.command_type == CommandType.LOCAL_JSX

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = FeedbackCommand()
        assert "/feedback" in cmd.get_help()

    @pytest.mark.asyncio
    async def test_execute_no_args_returns_jsx(self) -> None:
        """Test execute with no arguments returns Feedback form."""
        cmd = FeedbackCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "Feedback"
        assert result.node["props"]["initialDescription"] == ""

    @pytest.mark.asyncio
    async def test_execute_with_args(self) -> None:
        """Test execute with description argument."""
        cmd = FeedbackCommand()
        result = await cmd.execute("Bug in file editing", {})

        assert result.type == "jsx"
        assert result.node["type"] == "Feedback"
        assert result.node["props"]["initialDescription"] == "Bug in file editing"

    @pytest.mark.asyncio
    async def test_bug_alias(self) -> None:
        """Test /bug alias works."""
        cmd = FeedbackCommand()
        assert "bug" in cmd.aliases
        assert cmd.check_availability("all") is True
