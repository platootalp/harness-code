"""
Tests for commands/rate_limit_options.py - Rate Limit Options command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.rate_limit_options import RateLimitOptionsCommand


class TestRateLimitOptionsCommand:
    """Tests for RateLimitOptionsCommand."""

    def test_create(self) -> None:
        """Test creating RateLimitOptionsCommand."""
        cmd = RateLimitOptionsCommand()
        assert cmd.name == "rate-limit-options"
        assert cmd.description == "Show options when rate limit is reached"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.is_hidden is True
        assert cmd.source == "builtin"

    @pytest.mark.asyncio
    async def test_execute_returns_jsx(self) -> None:
        """Test execute returns JSX node for TUI rendering."""
        cmd = RateLimitOptionsCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "rate-limit-options"
