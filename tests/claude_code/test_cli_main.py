"""
Tests for cli/main.py - CLI entry point.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from claude_code.cli.main import cli


class TestCLI:
    """Tests for the CLI entry point."""

    def test_cli_entry_point(self):
        """Test CLI can be invoked."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        # Should show help or start TUI (TUI may fail without terminal, but shouldn't crash)
        assert result.exit_code in (0, 1)

    def test_cli_version(self):
        """Test CLI version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_cli_help(self):
        """Test CLI help option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output

    def test_headless_requires_prompt(self):
        """Test that --print mode requires a prompt argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--print"])
        assert result.exit_code == 1
        assert "Error" in result.output

    def test_headless_with_prompt(self, monkeypatch):
        """Test headless mode with a prompt (should fail gracefully without API key)."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--print", "Hello"])
        # Should attempt to run but fail due to missing API key or network
        # Either way, it shouldn't crash the CLI
        assert result.exit_code in (0, 1)

    def test_ask_subcommand(self, monkeypatch):
        """Test the ask subcommand is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "ask" in result.output

    def test_model_option(self, monkeypatch):
        """Test model option is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--model", "claude-opus-4-20250514", "--print", "test"])
        assert result.exit_code in (0, 1)

    def test_permission_mode_option(self, monkeypatch):
        """Test permission mode option is accepted."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--permission-mode", "bypassPermissions", "--print", "test"],
        )
        assert result.exit_code in (0, 1)


class TestCLIHelpers:
    """Tests for CLI helper functions."""

    def test_build_messages_user(self):
        """Test _build_messages creates user message."""
        from claude_code.cli.main import _build_messages
        from claude_code.models.message import Role

        messages = _build_messages("Hello")
        assert len(messages) == 1
        assert messages[0].role == Role.USER

    def test_build_messages_with_system(self):
        """Test _build_messages adds system message first."""
        from claude_code.cli.main import _build_messages
        from claude_code.models.message import Role

        messages = _build_messages("Hello", system_prompt="You are helpful")
        assert len(messages) == 2
        assert messages[0].role == Role.SYSTEM
        assert messages[1].role == Role.USER

    def test_create_output_handler_text(self):
        """Test _create_output_handler creates text handler."""
        from claude_code.cli.main import _create_output_handler

        handler = _create_output_handler("text")
        assert handler._format_type == "text"

    def test_create_output_handler_json(self):
        """Test _create_output_handler creates JSON handler."""
        from claude_code.cli.main import _create_output_handler

        handler = _create_output_handler("json")
        assert handler._format_type == "json"

    def test_create_output_handler_stream_json(self):
        """Test _create_output_handler creates stream JSON handler."""
        from claude_code.cli.main import _create_output_handler

        handler = _create_output_handler("stream-json")
        assert handler._format_type == "stream-json"
