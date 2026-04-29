"""MCP Client - connects to external MCP servers via stdio JSON-RPC."""
from __future__ import annotations

import asyncio
import json
import warnings
from dataclasses import dataclass, field
from typing import Any

from .types import MCPServerConfig, MCPTool, MCPResource, MCPResourceResult, MCPError


class MCPClient:
    """
    MCP Client - connects to external MCP servers via stdio.

    Uses the MCP JSON-RPC protocol over stdio for server communication.
    """

    def __init__(
        self,
        config: MCPServerConfig,
        timeout: float = 30.0,
    ):
        self.config = config
        self.timeout = timeout
        self._process: asyncio.subprocess.Process | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.StreamReader | None = None
        self._request_id: int = 0
        self._lock = asyncio.Lock()
        self._connected: bool = False

    async def connect(self) -> None:
        """Connect to the MCP server by spawning the server process."""
        if self._connected:
            return

        cmd = self.config.command
        args = [cmd] + self.config.args
        env = {**self.config.env} if self.config.env else None

        try:
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            self._writer = self._process.stdin
            self._reader = self._process.stdout
            self._connected = True

            # Send initialize request
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "src_py", "version": "1.0"},
            })

            # Send initialized notification
            await self._send_notification("initialized", {})

        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to MCP server '{self.config.name}': {e}")

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._process and self._connected:
            try:
                await self._send_notification("shutdown", {})
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except Exception:
                self._process.kill()
            finally:
                self._process = None
                self._writer = None
                self._reader = None
                self._connected = False

    async def list_tools(self) -> list[MCPTool]:
        """List all tools available from the MCP server."""
        if not self._connected:
            await self.connect()

        try:
            response = await self._send_request("tools/list", {})
            tools_data = response.get("tools", [])
            return [
                MCPTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {}),
                )
                for t in tools_data
            ]
        except Exception as e:
            warnings.warn(f"Failed to list tools from {self.config.name}: {e}")
            return []

    async def call_tool(
        self,
        tool: MCPTool,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        """Call an MCP tool with arguments."""
        if not self._connected:
            await self.connect()

        response = await self._send_request("tools/call", {
            "name": tool.name,
            "arguments": args,
        })

        content = response.get("content", [])
        if isinstance(content, list):
            result_texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        result_texts.append(block.get("text", ""))
                    elif block.get("type") == "image":
                        result_texts.append(f"[Image: {block.get('data', '')}]")
                    elif block.get("type") == "resource":
                        result_texts.append(block.get("resource", {}).get("text", ""))
                else:
                    result_texts.append(str(block))
            return {"result": "\n".join(result_texts)}
        return {"result": str(content)}

    async def list_resources(self) -> list[MCPResource]:
        """List all resources available from the MCP server."""
        if not self._connected:
            await self.connect()

        try:
            response = await self._send_request("resources/list", {})
            resources_data = response.get("resources", [])
            return [
                MCPResource(
                    uri=r.get("uri", ""),
                    name=r.get("name", ""),
                    description=r.get("description"),
                )
                for r in resources_data
            ]
        except Exception as e:
            warnings.warn(f"Failed to list resources from {self.config.name}: {e}")
            return []

    async def read_resource(self, uri: str) -> MCPResourceResult:
        """Read a specific resource by URI."""
        if not self._connected:
            await self.connect()

        response = await self._send_request("resources/read", {"uri": uri})
        contents = response.get("contents", [])
        if not contents:
            return MCPResourceResult(uri=uri, content="")

        block = contents[0]
        if isinstance(block, dict):
            if block.get("type") == "resource":
                res = block.get("resource", {})
                return MCPResourceResult(
                    uri=uri,
                    content=res.get("text", ""),
                    mime_type=res.get("mimeType"),
                )
            elif block.get("type") == "text":
                return MCPResourceResult(uri=uri, content=block.get("text", ""))
        return MCPResourceResult(uri=uri, content=str(block))

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response."""
        async with self._lock:
            self._request_id += 1
            req_id = self._request_id

            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }

            data = json.dumps(payload).encode() + b"\n"
            if self._writer is None:
                raise ConnectionError("Not connected to MCP server")
            self._writer.write(data)
            await self._writer.drain()

            if self._reader is None:
                raise ConnectionError("Not connected to MCP server")
            line = await asyncio.wait_for(
                self._reader.readline(),
                timeout=self.timeout,
            )
            if not line:
                raise ConnectionError("MCP server closed connection")

            response = json.loads(line.decode())
            if "error" in response:
                raise MCPError(
                    code=response["error"].get("code", -32603),
                    message=response["error"].get("message", "Unknown error"),
                )
            return response.get("result", {})

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        async with self._lock:
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
            data = json.dumps(payload).encode() + b"\n"
            if self._writer:
                self._writer.write(data)
                await self._writer.drain()
