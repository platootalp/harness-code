"""
Tests for commands/install_github_app.py - Install GitHub App command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandType
from claude_code.commands.install_github_app import InstallGithubAppCommand


class TestInstallGithubAppCommand:
    """Tests for InstallGithubAppCommand."""

    def test_create(self) -> None:
        """Test creating InstallGithubAppCommand."""
        cmd = InstallGithubAppCommand()
        assert cmd.name == "install-github-app"
        assert cmd.description == "Set up Claude GitHub Actions for a repository"
        assert cmd.command_type == CommandType.LOCAL
        assert cmd.source == "builtin"

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = InstallGithubAppCommand()
        help_text = cmd.get_help()
        assert "install-github-app" in help_text

    @pytest.mark.asyncio
    async def test_execute_returns_text(self) -> None:
        """Test execute returns text with GitHub app info."""
        cmd = InstallGithubAppCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        assert result.value is not None
        assert "GitHub" in (result.value or "")

    @pytest.mark.asyncio
    async def test_execute_mentions_setup(self) -> None:
        """Test execute mentions setup options."""
        cmd = InstallGithubAppCommand()
        result = await cmd.execute("", {})

        assert result.type == "text"
        text = result.value or ""
        assert "setup" in text.lower() or "GitHub Actions" in text
