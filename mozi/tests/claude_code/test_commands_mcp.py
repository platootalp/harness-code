"""
Tests for MCP command.
"""

from __future__ import annotations

import pytest

from claude_code.commands.base import CommandResult, CommandType
from claude_code.commands.mcp import McpCommand


class TestMcpCommand:
    """Tests for McpCommand."""

    def test_create(self) -> None:
        """Test creating McpCommand."""
        cmd = McpCommand()
        assert cmd.name == "mcp"
        assert cmd.description == "Manage MCP servers"
        assert cmd.argument_hint == "[enable|disable [server-name]]"
        assert cmd.command_type == CommandType.LOCAL_JSX
        assert cmd.source == "builtin"
        assert cmd.immediate is True

    def test_get_help(self) -> None:
        """Test get_help."""
        cmd = McpCommand()
        help_text = cmd.get_help()
        assert "/mcp" in help_text

    @pytest.mark.asyncio
    async def test_execute_no_args_returns_jsx(self) -> None:
        """Test execute with no args returns settings JSX."""
        cmd = McpCommand()
        result = await cmd.execute("", {})

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "mcp"
        assert result.node["mode"] == "settings"

    @pytest.mark.asyncio
    async def test_execute_enable_all(self) -> None:
        """Test enable all MCP servers."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "disabled"},
                    {"name": "server2", "type": "disabled"},
                ]
            }
        }

        result = await cmd.execute("enable", context)

        assert result.type == "text"
        assert "Enabled 2" in result.value

    @pytest.mark.asyncio
    async def test_execute_disable_all(self) -> None:
        """Test disable all MCP servers."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "connected"},
                    {"name": "server2", "type": "connected"},
                ]
            }
        }

        result = await cmd.execute("disable", context)

        assert result.type == "text"
        assert "Disabled 2" in result.value

    @pytest.mark.asyncio
    async def test_execute_enable_specific(self) -> None:
        """Test enable specific server."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "disabled"},
                    {"name": "server2", "type": "disabled"},
                ]
            }
        }

        result = await cmd.execute("enable server1", context)

        assert result.type == "text"
        assert 'server "server1" enabled' in result.value

    @pytest.mark.asyncio
    async def test_execute_disable_specific(self) -> None:
        """Test disable specific server."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "connected"},
                    {"name": "server2", "type": "connected"},
                ]
            }
        }

        result = await cmd.execute("disable server1", context)

        assert result.type == "text"
        assert 'server "server1" disabled' in result.value

    @pytest.mark.asyncio
    async def test_execute_enable_already_enabled(self) -> None:
        """Test enable when all already enabled."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "connected"},
                ]
            }
        }

        result = await cmd.execute("enable", context)

        assert result.type == "text"
        assert "already enabled" in result.value

    @pytest.mark.asyncio
    async def test_execute_disable_already_disabled(self) -> None:
        """Test disable when all already disabled."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "disabled"},
                ]
            }
        }

        result = await cmd.execute("disable", context)

        assert result.type == "text"
        assert "already disabled" in result.value

    @pytest.mark.asyncio
    async def test_execute_enable_server_not_found(self) -> None:
        """Test enable non-existent server."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "connected"},
                ]
            }
        }

        result = await cmd.execute("enable nonexistent", context)

        assert result.type == "text"
        assert "not found" in result.value

    @pytest.mark.asyncio
    async def test_execute_reconnect_returns_jsx(self) -> None:
        """Test reconnect returns JSX node."""
        cmd = McpCommand()
        context = {}

        result = await cmd.execute("reconnect my-server", context)

        assert result.type == "jsx"
        assert result.node is not None
        assert result.node["type"] == "mcp"
        assert result.node["mode"] == "reconnect"
        assert result.node["server_name"] == "my-server"

    @pytest.mark.asyncio
    async def test_execute_reconnect_requires_name(self) -> None:
        """Test reconnect requires server name."""
        cmd = McpCommand()
        context = {}

        result = await cmd.execute("reconnect", context)

        assert result.type == "text"
        assert "Error" in result.value
        assert "required" in result.value

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self) -> None:
        """Test unknown action returns error."""
        cmd = McpCommand()
        context = {}

        result = await cmd.execute("unknown", context)

        assert result.type == "text"
        assert "Unknown MCP command" in result.value

    @pytest.mark.asyncio
    async def test_execute_ignores_ide_server(self) -> None:
        """Test that ide server is not toggled."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "ide", "type": "disabled"},
                    {"name": "server1", "type": "disabled"},
                ]
            }
        }

        result = await cmd.execute("enable", context)

        assert result.type == "text"
        assert "Enabled 1" in result.value

    @pytest.mark.asyncio
    async def test_execute_no_mcp_state(self) -> None:
        """Test execute with no MCP state context."""
        cmd = McpCommand()
        context = {}

        result = await cmd.execute("enable", context)

        assert result.type == "text"
        # No clients means nothing to enable (already enabled)
        assert "already enabled" in result.value

    @pytest.mark.asyncio
    async def test_execute_with_whitespace(self) -> None:
        """Test execute handles whitespace correctly."""
        cmd = McpCommand()
        context = {
            "_mcp_state": {
                "clients": [
                    {"name": "server1", "type": "connected"},
                ]
            }
        }

        result = await cmd.execute("  disable   server1  ", context)

        assert result.type == "text"
        assert 'server "server1" disabled' in result.value
