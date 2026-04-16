"""MCP command for Claude Code.

Manages MCP (Model Context Protocol) servers.

TypeScript equivalent: src/commands/mcp/mcp.tsx, src/commands/mcp/addCommand.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import BaseCommand, CommandResult, CommandType

if TYPE_CHECKING:
    pass


@dataclass
class McpCommand(BaseCommand):
    """Manage MCP servers.

    Provides management interface for MCP (Model Context Protocol) servers.
    Can enable/disable servers, show settings, or reconnect to servers.

    TypeScript equivalent: src/commands/mcp/mcp.tsx
    """

    name: str = "mcp"
    description: str = "Manage MCP servers"
    argument_hint: str | None = "[enable|disable [server-name]]"
    command_type: CommandType = CommandType.LOCAL_JSX
    source: str = "builtin"
    immediate: bool = True

    def __post_init__(self) -> None:
        self._all_names: set[str] = {self.name}

    async def execute(
        self,
        args: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Execute the MCP command.

        Args:
            args: Command arguments. Can be:
                - "enable [server-name]" to enable MCP server(s)
                - "disable [server-name]" to disable MCP server(s)
                - "reconnect [server-name]" to reconnect to a server
                - "" (empty) to show MCP settings
            context: Execution context.

        Returns:
            CommandResult with appropriate output.
        """
        trimmed = args.strip() if args.strip() else ""

        if not trimmed:
            return self._show_settings(context)

        parts = trimmed.split()
        action = parts[0].lower()

        if action == "enable":
            target = " ".join(parts[1:]) if len(parts) > 1 else "all"
            return self._toggle_server("enable", target, context)
        elif action == "disable":
            target = " ".join(parts[1:]) if len(parts) > 1 else "all"
            return self._toggle_server("disable", target, context)
        elif action == "reconnect":
            if len(parts) < 2:
                return CommandResult(
                    type="text",
                    value="Error: Server name required. Usage: /mcp reconnect <server-name>",
                )
            server_name = " ".join(parts[1:])
            return self._reconnect_server(server_name, context)
        else:
            return CommandResult(
                type="text",
                value=f"Unknown MCP command: {action}\n"
                + "Usage: /mcp [enable|disable|reconnect] [server-name]",
            )

    def _show_settings(self, context: dict[str, Any]) -> CommandResult:
        """Show MCP settings panel.

        Args:
            context: Execution context.

        Returns:
            CommandResult with JSX node for MCP settings.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "mcp",
                "mode": "settings",
                "context": context,
            },
        )

    def _toggle_server(
        self,
        action: str,
        target: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Enable or disable an MCP server.

        Args:
            action: "enable" or "disable".
            target: Server name or "all".
            context: Execution context.

        Returns:
            CommandResult with result message.
        """
        mcp_state: dict[str, Any] | None = context.get("_mcp_state")
        clients: list[dict[str, Any]] = []
        if mcp_state and "clients" in mcp_state:
            clients = mcp_state["clients"]

        # Filter out ide server
        non_ide_clients = [c for c in clients if c.get("name") != "ide"]

        is_enabling = action == "enable"
        if target == "all":
            if is_enabling:
                to_toggle = [c for c in non_ide_clients if c.get("type") == "disabled"]
            else:
                to_toggle = [c for c in non_ide_clients if c.get("type") != "disabled"]
        else:
            to_toggle = [c for c in non_ide_clients if c.get("name") == target]

        if not to_toggle:
            if target == "all":
                status = "enabled" if is_enabling else "disabled"
                return CommandResult(
                    type="text",
                    value=f"All MCP servers are already {status}.",
                )
            else:
                return CommandResult(
                    type="text",
                    value=f'MCP server "{target}" not found.',
                )

        # Apply toggle to state
        if mcp_state:
            for server in to_toggle:
                name = server.get("name", "")
                for client in clients:
                    if client.get("name") == name:
                        if is_enabling:
                            client["type"] = "connected"
                        else:
                            client["type"] = "disabled"
                        break

        count = len(to_toggle)
        if target == "all":
            status = "Enabled" if is_enabling else "Disabled"
            return CommandResult(
                type="text",
                value=f"{status} {count} MCP server(s).",
            )
        else:
            status = "enabled" if is_enabling else "disabled"
            return CommandResult(
                type="text",
                value=f'MCP server "{target}" {status}.',
            )

    def _reconnect_server(
        self,
        server_name: str,
        context: dict[str, Any],
    ) -> CommandResult:
        """Reconnect to an MCP server.

        Args:
            server_name: Name of the server to reconnect.
            context: Execution context.

        Returns:
            CommandResult with JSX node for reconnection.
        """
        return CommandResult(
            type="jsx",
            value=None,
            node={
                "type": "mcp",
                "mode": "reconnect",
                "server_name": server_name,
                "context": context,
            },
        )
