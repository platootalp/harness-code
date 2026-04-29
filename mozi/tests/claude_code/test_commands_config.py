"""
Tests for commands/config.py - Config command.
"""

from __future__ import annotations

from claude_code.commands.config import ConfigCommand


class TestConfigCommand:
    """Tests for ConfigCommand."""

    def test_name(self) -> None:
        assert ConfigCommand().name == "config"

    def test_description(self) -> None:
        assert "config" in ConfigCommand().description.lower()
        assert "panel" in ConfigCommand().description.lower()

    def test_aliases(self) -> None:
        assert "settings" in ConfigCommand().aliases

    def test_source(self) -> None:
        assert ConfigCommand().source == "builtin"

    def test_command_type_local_jsx(self) -> None:
        """ConfigCommand is a LOCAL_JSX command."""
        from claude_code.commands.base import CommandType

        cmd = ConfigCommand()
        assert cmd.command_type == CommandType.LOCAL_JSX

    def test_get_help(self) -> None:
        assert "/config" in ConfigCommand().get_help()

    def test_all_names_includes_aliases(self) -> None:
        cmd = ConfigCommand()
        assert "config" in cmd._all_names
        assert "settings" in cmd._all_names

    def test_execute_returns_jsx(self) -> None:
        """execute returns JSX-type CommandResult."""
        cmd = ConfigCommand()

        import asyncio

        result = asyncio.run(cmd.execute("", {}))

        assert result.type == "jsx"
        assert result.value is None
        assert result.node is not None
        assert result.node["type"] == "config"
        assert result.node["tab"] == "Config"

    def test_execute_passes_context(self) -> None:
        """execute passes context to the node."""
        cmd = ConfigCommand()
        context = {"user": "test"}

        import asyncio

        result = asyncio.run(cmd.execute("", {"_repl_state": context}))

        assert result.node["context"] == {"_repl_state": context}
