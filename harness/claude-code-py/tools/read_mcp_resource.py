"""
ReadMcpResourceTool - Read a specific MCP resource by URI.

Migrated from src/tools/ReadMcpResourceTool/ReadMcpResourceTool.ts.
"""

from __future__ import annotations

import base64
import mimetypes
import os
import tempfile
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

READ_MCP_RESOURCE_TOOL_NAME = "ReadMcpResource"


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class ResourceContent:
    """A single resource content item."""

    uri: str
    mime_type: str | None = None
    text: str | None = None
    blob_saved_to: str | None = None


@dataclass
class ReadMcpResourceToolOutput:
    """Output from the ReadMcpResourceTool."""

    contents: list[ResourceContent] = field(default_factory=list)


# =============================================================================
# ReadMcpResourceTool
# =============================================================================


class ReadMcpResourceTool(BaseTool):
    """Tool for reading a specific MCP resource by URI.

    Connects to an MCP server and reads the content of a resource identified
    by its URI. Supports both text and binary (blob) content.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "read a specific MCP resource by URI"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = False

    def __init__(self) -> None:
        self.should_defer = True

    @property
    def name(self) -> str:
        return READ_MCP_RESOURCE_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "The MCP server name",
                },
                "uri": {
                    "type": "string",
                    "description": "The resource URI to read",
                },
            },
            "required": ["server", "uri"],
        }

    @property
    def output_schema(self) -> dict[str, Any] | None:
        return {
            "type": "object",
            "properties": {
                "contents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "uri": {"type": "string"},
                            "mimeType": {"type": "string"},
                            "text": {"type": "string"},
                            "blobSavedTo": {"type": "string"},
                        },
                    },
                },
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return READ_MCP_RESOURCE_TOOL_NAME

    def is_enabled(self) -> bool:
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def to_auto_classifier_input(self, input: Any) -> str:
        return f"{input.get('server', '')} {input.get('uri', '')}"

    async def validate_input(
        self, input: Any, context: ToolUseContext
    ) -> ValidationResult:
        """Schema validation handles required fields."""
        return True

    def _get_mcp_clients(self, context: ToolUseContext) -> list[Any]:
        """Extract MCP clients from context."""
        if hasattr(context, "mcp_clients"):
            return context.mcp_clients or []
        return []

    def _find_client(self, server_name: str, mcp_clients: list[Any]) -> Any | None:
        """Find an MCP client by name."""
        for client in mcp_clients:
            if getattr(client, "name", None) == server_name:
                return client
        return None

    async def _ensure_connected_client(self, client: Any) -> Any:
        """Ensure the MCP client is connected."""
        state = getattr(client, "state", None)
        if state and str(state) != "connected":
            await client.connect()
        return client

    async def _read_resource(
        self, client: Any, uri: str
    ) -> dict[str, Any]:
        """Read a resource from the MCP client."""
        try:
            result: dict[str, Any] = await client.send_request("resources/read", {"uri": uri})
            return result
        except Exception as e:
            return {"contents": [], "error": str(e)}

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[ReadMcpResourceToolOutput]:
        """Execute the tool to read an MCP resource."""
        server_name = args.get("server", "")
        uri = args.get("uri", "")

        mcp_clients = self._get_mcp_clients(context)

        if not mcp_clients:
            output = ReadMcpResourceToolOutput(contents=[])
            return ToolResult(data=output)

        client = self._find_client(server_name, mcp_clients)
        if client is None:
            available = ", ".join(
                getattr(c, "name", "unknown") for c in mcp_clients
            )
            output = ReadMcpResourceToolOutput(
                contents=[
                    ResourceContent(
                        uri=uri,
                        text=f'Server "{server_name}" not found. Available servers: {available}',
                    )
                ]
            )
            return ToolResult(data=output)

        try:
            connected_client = await self._ensure_connected_client(client)
            result = await self._read_resource(connected_client, uri)

            contents: list[ResourceContent] = []
            raw_contents = result.get("contents", [])

            for i, c in enumerate(raw_contents):
                if isinstance(c, dict):
                    text = c.get("text")
                    blob = c.get("blob")
                    mime_type = c.get("mimeType")
                    content_uri = c.get("uri", uri)

                    if text is not None:
                        contents.append(
                            ResourceContent(
                                uri=content_uri,
                                mime_type=mime_type,
                                text=text,
                            )
                        )
                    elif blob and isinstance(blob, str):
                        saved_path, saved_msg = self._persist_blob(
                            blob, mime_type, i, server_name
                        )
                        contents.append(
                            ResourceContent(
                                uri=content_uri,
                                mime_type=mime_type,
                                blob_saved_to=saved_path,
                                text=saved_msg,
                            )
                        )
                    else:
                        contents.append(
                            ResourceContent(
                                uri=content_uri,
                                mime_type=mime_type,
                            )
                        )
                elif hasattr(c, "text") and c.text is not None:
                    contents.append(
                        ResourceContent(
                            uri=getattr(c, "uri", uri),
                            mime_type=getattr(c, "mimeType", None),
                            text=c.text,
                        )
                    )
                elif hasattr(c, "blob"):
                    blob = c.blob
                    mime_type = getattr(c, "mimeType", "application/octet-stream")
                    saved_path, saved_msg = self._persist_blob(
                        str(blob), mime_type, i, server_name
                    )
                    contents.append(
                        ResourceContent(
                            uri=getattr(c, "uri", uri),
                            mime_type=mime_type,
                            blob_saved_to=saved_path,
                            text=saved_msg,
                        )
                    )

            output = ReadMcpResourceToolOutput(contents=contents)
            return ToolResult(data=output)

        except Exception as e:
            output = ReadMcpResourceToolOutput(
                contents=[
                    ResourceContent(
                        uri=uri,
                        text=f"Error reading resource: {e}",
                    )
                ]
            )
            return ToolResult(data=output)

    def _persist_blob(
        self, blob_data: str, mime_type: str | None, index: int, server_name: str
    ) -> tuple[str, str]:
        """Save binary blob to disk. Returns (path, message)."""
        mime_type = mime_type or "application/octet-stream"

        # Determine extension from mime type
        ext = mimetypes.guess_extension(mime_type) or ""
        if ext == ".js":
            ext = ".mjs"

        persist_id = f"mcp-resource-{index}-{server_name}"
        try:
            fd, filepath = tempfile.mkstemp(suffix=ext, prefix=persist_id)
            os.close(fd)

            data = base64.b64decode(blob_data)
            with open(filepath, "wb") as f:
                f.write(data)

            msg = (
                f"[Resource from {server_name}] "
                f"Binary content ({mime_type}, {len(data)} bytes) saved to: {filepath}"
            )
            return filepath, msg
        except Exception as e:
            return "", f"Binary content could not be saved: {e}"

    async def description(
        self, input: Any, options: dict[str, Any]
    ) -> str:
        return (
            "A tool for reading MCP resources by their URI. "
            "Specify the MCP server name and the resource URI to retrieve content. "
            "Supports both text and binary content."
        )

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "Use this tool to read resources from MCP servers. "
            "Provide the server name and the resource URI. "
            "Text content is returned directly; binary content is saved to disk "
            "and the path is returned."
        )
