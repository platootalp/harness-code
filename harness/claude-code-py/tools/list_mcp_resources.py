"""
ListMcpResourcesTool - List available MCP resources from all connected servers.

Migrated from src/tools/ListMcpResourcesTool/ListMcpResourcesTool.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

LIST_MCP_RESOURCES_TOOL_NAME = "ListMcpResources"


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class ListMcpResourcesToolOutput:
    """Output from the ListMcpResourcesTool."""

    resources: list[dict[str, Any]] = field(default_factory=list)
    server_filter: str | None = None


# =============================================================================
# ListMcpResourcesTool
# =============================================================================


class ListMcpResourcesTool(BaseTool):
    """Tool for listing available MCP resources from all connected servers.

    Queries all connected MCP servers and returns a list of available resources
    that can be read using the ReadMcpResource tool.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "list available MCP resources from connected servers"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    def __init__(self) -> None:
        self.should_defer = True

    @property
    def name(self) -> str:
        return LIST_MCP_RESOURCES_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "Optional server name to filter resources by",
                },
            },
            "required": [],
        }

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "name": {"type": "string"},
                    "mimeType": {"type": "string"},
                    "description": {"type": "string"},
                    "server": {"type": "string"},
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return LIST_MCP_RESOURCES_TOOL_NAME

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return str(input.get("server", ""))

    async def validate_input(
        self, input: Any, context: ToolUseContext
    ) -> ValidationResult:
        """Schema validation handles required fields."""
        return True

    def _find_server(self, server_name: str, mcp_clients: list[Any]) -> Any:
        """Find an MCP client by name."""
        for client in mcp_clients:
            if getattr(client, "name", None) == server_name:
                return client
        available = ", ".join(
            getattr(c, "name", "unknown") for c in mcp_clients
        )
        raise Exception(
            f'Server "{server_name}" not found. Available servers: {available}'
        )

    async def _ensure_connected_client(self, client: Any) -> Any:
        """Ensure the MCP client is connected."""
        state = getattr(client, "state", None)
        if state and str(state) != "connected":
            await client.connect()
        return client

    async def _fetch_resources_for_client(self, client: Any) -> list[Any]:
        """Fetch resources from an MCP client."""
        try:
            result: list[Any] = await client.list_resources()
            return result
        except Exception:
            return []

    def _client_has_resources(self, client: Any) -> bool:
        """Check if a client has resource capabilities."""
        capabilities = getattr(client, "capabilities", None)
        if capabilities:
            return getattr(capabilities, "resources", False)
        return False

    def _format_resource(self, resource: Any, server_name: str) -> dict[str, Any]:
        """Format a resource for output."""
        result: dict[str, Any] = {
            "uri": getattr(resource, "uri", ""),
            "name": getattr(resource, "name", ""),
            "server": server_name,
        }
        mime_type = getattr(resource, "mimeType", None)
        if mime_type:
            result["mimeType"] = mime_type
        description = getattr(resource, "description", None)
        if description:
            result["description"] = description
        return result

    def _get_mcp_clients(self, context: ToolUseContext) -> list[Any]:
        """Extract MCP clients from context."""
        mcp_clients: list[Any] = []
        if hasattr(context, "mcp_clients"):
            mcp_clients = context.mcp_clients or []
        elif hasattr(context, "tools"):
            pass
        return mcp_clients

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[ListMcpResourcesToolOutput]:
        """Execute the tool to list MCP resources."""
        server_filter = args.get("server")
        mcp_clients = self._get_mcp_clients(context)

        if not mcp_clients:
            output = ListMcpResourcesToolOutput(resources=[], server_filter=server_filter)
            return ToolResult(data=output)

        resources: list[dict[str, Any]] = []

        if server_filter:
            # Filter to specific server
            try:
                client = self._find_server(server_filter, mcp_clients)
                connected_client = await self._ensure_connected_client(client)
                if connected_client and self._client_has_resources(connected_client):
                    server_resources = await self._fetch_resources_for_client(
                        connected_client
                    )
                    for resource in server_resources:
                        resources.append(
                            self._format_resource(resource, str(server_filter))
                        )
            except Exception:
                pass
        else:
            # Query all connected servers
            for client in mcp_clients:
                client_type = getattr(client, "type", None)
                if client_type and str(client_type) != "connected":
                    continue
                try:
                    connected_client = await self._ensure_connected_client(client)
                    if connected_client and self._client_has_resources(connected_client):
                        server_resources = await self._fetch_resources_for_client(
                            connected_client
                        )
                        for resource in server_resources:
                            resources.append(
                                self._format_resource(
                                    resource, getattr(client, "name", "unknown")
                                )
                            )
                except Exception:
                    pass

        output = ListMcpResourcesToolOutput(
            resources=resources, server_filter=server_filter
        )
        return ToolResult(data=output)

    async def description(
        self, input: Any, options: dict[str, Any]
    ) -> str:
        return (
            "A tool for listing all available MCP resources from connected servers. "
            "Returns a list of resources with their URIs, names, and metadata. "
            "Use this to discover what resources are available before reading them."
        )

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "Use this tool to list available MCP resources from all connected servers. "
            "Optionally filter by server name to list resources from a specific server."
        )
