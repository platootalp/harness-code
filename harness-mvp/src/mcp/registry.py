"""MCP Registry - unified management of MCP clients and servers."""
from __future__ import annotations

import warnings
from typing import Any

from .client import MCPClient
from .server import MCPServer
from .types import MCPTool


class MCPRegistry:
    """
    Unified MCP registry - manages both clients and servers.

    Handles:
    - Multiple MCP client connections
    - Multiple local FastMCP servers
    - Tool name collision resolution via prefix
    - Cached merged tool list

    Collision resolution strategy:
    When two servers expose tools with the same name, the conflicting
    tool is renamed to "{server_name}__{original_name}" to ensure
    uniqueness. A warning is emitted.
    """

    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
        self.servers: dict[str, MCPServer] = {}
        self._tool_cache: list[MCPTool] = []
        self._cache_valid: bool = False

    def add_client(self, name: str, client: MCPClient) -> None:
        """Add an MCP client connection."""
        self.clients[name] = client
        self._cache_valid = False

    def add_server(self, name: str, server: MCPServer) -> None:
        """Add a local MCP server."""
        self.servers[name] = server
        self._cache_valid = False

    async def connect_all(self) -> None:
        """Connect all registered MCP clients."""
        for name, client in self.clients.items():
            try:
                await client.connect()
            except Exception as e:
                warnings.warn(f"Failed to connect MCP client '{name}': {e}")

    async def disconnect_all(self) -> None:
        """Disconnect all MCP clients."""
        for name, client in self.clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                warnings.warn(f"Error disconnecting MCP client '{name}': {e}")

    def get_tools(self) -> list[MCPTool]:
        """
        Get all tools from all connected MCP clients and servers.

        Merges tool lists with collision resolution:
        - Tools with unique names are kept as-is
        - Tools with name collisions are renamed: "{server}__" prefix

        Results are cached until a client/server is added/removed.
        """
        if self._cache_valid:
            return self._tool_cache

        all_tools: list[MCPTool] = []
        tool_names: dict[str, str] = {}  # tool_name -> server_name

        # Collect from clients
        for server_name, client in self.clients.items():
            try:
                tools = client.list_tools()
                for tool in tools:
                    if tool.name in tool_names:
                        original_server = tool_names[tool.name]
                        tool.name = f"{server_name}__{tool.name}"
                        warnings.warn(
                            f"Tool name collision: '{tool.name}' from '{original_server}' "
                            f"renamed to '{tool.name}' due to conflict with '{server_name}'"
                        )
                        tool_names[f"{server_name}__{tool.name}"] = server_name
                    else:
                        tool_names[tool.name] = server_name
                    all_tools.append(tool)
            except Exception as e:
                warnings.warn(f"Failed to list tools from client '{server_name}': {e}")

        # Collect from servers
        for server_name, server in self.servers.items():
            tools = server.get_tools()
            for tool in tools:
                if tool.name in tool_names:
                    original_server = tool_names[tool.name]
                    tool.name = f"{server_name}__{tool.name}"
                    warnings.warn(
                        f"Tool name collision: '{tool.name}' from '{original_server}' "
                        f"renamed to '{tool.name}' due to conflict with '{server_name}'"
                    )
                else:
                    tool_names[tool.name] = server_name
                all_tools.append(tool)

        self._tool_cache = all_tools
        self._cache_valid = True
        return all_tools

    def list_servers(self) -> list[str]:
        """List all registered server and client names."""
        return list(self.clients.keys()) + list(self.servers.keys())

    async def call_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool by name, routing to the appropriate client/server.

        Args:
            tool_name: Tool name (may be collision-resolved with "__" prefix).
            args: Tool arguments.

        Returns:
            Tool execution result.
        """
        # Check if it's a collision-resolved name
        if "__" in tool_name:
            parts = tool_name.split("__", 1)
            prefix, original_name = parts[0], parts[1]

            if prefix in self.clients:
                client = self.clients[prefix]
                tool = MCPTool(name=original_name, description="", input_schema={})
                return await client.call_tool(tool, args)

            if prefix in self.servers:
                server = self.servers[prefix]
                return await server.call_tool(original_name, args)

        # Try to find by original name in any client/server
        for client in self.clients.values():
            try:
                tools = client.list_tools()
                for t in tools:
                    if t.name == tool_name:
                        return await client.call_tool(t, args)
            except Exception:
                continue

        for server in self.servers.values():
            if tool_name in server._tools:
                return await server.call_tool(tool_name, args)

        raise KeyError(f"Tool not found: {tool_name}")
