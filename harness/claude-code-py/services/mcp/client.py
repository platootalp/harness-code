"""MCP client with multi-transport support.

TypeScript equivalent: src/services/mcp/client.ts
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class TransportType(StrEnum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"
    WS = "websocket"


class MCPClientState(StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class MCPClientConfig:
    """Configuration for MCP client."""

    transport_type: TransportType = TransportType.STDIO
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    timeout: float = 30.0


class MCPClient:
    """Async MCP client with transport abstraction."""

    def __init__(self, config: MCPClientConfig) -> None:
        """Initialize MCP client.

        Args:
            config: Client configuration.
        """
        self.config = config
        self._state = MCPClientState.IDLE
        self._protocol: Any = None  # Lazy import to avoid circular deps
        self._pending_requests: dict[str | int, asyncio.Future] = {}
        self._notification_handlers: dict[str, Callable] = {}
        self._process: asyncio.subprocess.Process | None = None
        self._transport: Any = None
        self._connected_event: asyncio.Event | None = None

    @property
    def state(self) -> MCPClientState:
        """Get current client state."""
        return self._state

    async def connect(self) -> None:
        """Connect to MCP server based on transport type."""
        if self._state == MCPClientState.CONNECTED:
            return

        self._state = MCPClientState.CONNECTING
        self._connected_event = asyncio.Event()

        try:
            if self.config.transport_type == TransportType.STDIO:
                await self._connect_stdio()
            elif self.config.transport_type == TransportType.SSE:
                await self._connect_sse()
            elif self.config.transport_type == TransportType.HTTP:
                await self._connect_http()
            elif self.config.transport_type == TransportType.WS:
                await self._connect_websocket()
            else:
                raise ValueError(f"Unknown transport type: {self.config.transport_type}")

            self._state = MCPClientState.CONNECTED
            self._connected_event.set()

            # Send initialize request
            await self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "claude-code",
                    "version": "1.0.0",
                },
            })

            # Send initialized notification
            await self.send_notification("initialized", {})

        except Exception:
            self._state = MCPClientState.ERROR
            if self._connected_event:
                self._connected_event.set()
            raise

    async def _connect_stdio(self) -> None:
        """Connect via STDIO transport."""
        if not self.config.command:
            raise ValueError("STDIO transport requires 'command' to be set")


        cmd = self.config.command
        args = self.config.args or []

        self._process = await asyncio.create_subprocess_exec(
            cmd,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.config.env,
        )

        # Start reader tasks
        asyncio.create_task(self._read_stdout())
        asyncio.create_task(self._read_stderr())

    async def _connect_sse(self) -> None:
        """Connect via SSE transport."""
        raise NotImplementedError("SSE transport not yet implemented")

    async def _connect_http(self) -> None:
        """Connect via HTTP/SSE transport."""
        raise NotImplementedError("HTTP transport not yet implemented")

    async def _connect_websocket(self) -> None:
        """Connect via WebSocket transport."""
        raise NotImplementedError("WebSocket transport not yet implemented")

    async def _read_stdout(self) -> None:
        """Read messages from stdout."""
        if not self._process or not self._process.stdout:
            return

        protocol = self._get_protocol()
        buffer = b""

        try:
            while True:
                chunk = await self._process.stdout.read(1024)
                if not chunk:
                    break
                buffer += chunk

                # Process complete messages (newline-delimited JSON)
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        await self._handle_message(protocol, line)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error reading stdout: %s", e)

    async def _read_stderr(self) -> None:
        """Read and log stderr output."""
        if not self._process or not self._process.stderr:
            return

        try:
            stderr_data = await self._process.stderr.read()
            if stderr_data:
                logger.debug("MCP server stderr: %s", stderr_data.decode())
        except Exception as e:
            logger.error("Error reading stderr: %s", e)

    def _get_protocol(self) -> Any:
        """Lazy-load protocol to avoid circular import."""
        if self._protocol is None:
            from claude_code.services.mcp.protocol import MCPProtocol
            self._protocol = MCPProtocol()
        return self._protocol

    async def _handle_message(self, protocol: Any, data: bytes | str) -> None:
        """Handle incoming message."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        msg = protocol.parse_message(data)
        if msg is None:
            return

        # Import here to avoid circular import at module level
        from claude_code.services.mcp.protocol import MCPResponse

        if isinstance(msg, MCPResponse):
            if msg.id is not None and msg.id in self._pending_requests:
                future = self._pending_requests.pop(msg.id)
                if not future.done():
                    if msg.error:
                        future.set_exception(Exception(msg.error.get("message", "Unknown error")))
                    else:
                        future.set_result(msg.result)
            elif msg.error:
                handler = self._notification_handlers.get("__error__")
                if handler:
                    handler(msg.error)
        else:
            # It's a request (could be notification or request)
            if msg.method in self._notification_handlers:
                handler = self._notification_handlers[msg.method]
                if msg.params:
                    asyncio.create_task(self._call_handler(handler, msg.params))

    async def _call_handler(self, handler: Callable, params: dict[str, Any]) -> None:
        """Call a notification handler."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(params)
            else:
                handler(params)
        except Exception as e:
            logger.error("Error in notification handler: %s", e)

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self._state == MCPClientState.DISCONNECTED:
            return

        # Cancel all pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()

        self._pending_requests.clear()

        # Terminate process if STDIO
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                self._process.kill()
            self._process = None

        self._state = MCPClientState.DISCONNECTED
        if self._connected_event:
            self._connected_event.set()

    async def send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: The method name to call.
            params: Optional parameters for the method.

        Returns:
            The result from the server.

        Raises:
            Exception: If the request fails or times out.
        """
        if self._state != MCPClientState.CONNECTED:
            raise RuntimeError(f"Client not connected (state: {self._state.value})")

        protocol = self._get_protocol()
        request_id = id(method) % 100000  # Simple numeric ID

        request = protocol.create_request(method, params, request_id)
        message = protocol.serialize_message(request)

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            await self._send_message(message)

            # Wait for response with timeout
            result = await asyncio.wait_for(
                future,
                timeout=self.config.timeout,
            )
            return result if result is not None else {}

        except TimeoutError as e:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request {method} timed out after {self.config.timeout}s") from e
        except Exception:
            self._pending_requests.pop(request_id, None)
            raise

    async def send_notification(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: The method name to notify.
            params: Optional parameters for the method.
        """
        if self._state != MCPClientState.CONNECTED:
            raise RuntimeError(f"Client not connected (state: {self._state.value})")

        protocol = self._get_protocol()
        notification = protocol.create_notification(method, params)
        message = protocol.serialize_message(notification)
        await self._send_message(message)

    async def _send_message(self, message: bytes) -> None:
        """Send a message via the current transport."""
        if self.config.transport_type == TransportType.STDIO:
            if self._process and self._process.stdin:
                self._process.stdin.write(message + b"\n")
                await self._process.stdin.drain()
        else:
            raise NotImplementedError(
                f"Message sending not implemented for transport: {self.config.transport_type}"
            )

    def on_notification(
        self,
        method: str,
        handler: Callable[[dict[str, Any]], None],
    ) -> None:
        """Register a notification handler.

        Args:
            method: The method name to handle.
            handler: Callback function to handle the notification.
        """
        self._notification_handlers[method] = handler

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools via tools/list method.

        Returns:
            List of available tools.
        """
        result = await self.send_request("tools/list")
        return result.get("tools", []) if result else []

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources via resources/list method.

        Returns:
            List of available resources.
        """
        result = await self.send_request("resources/list")
        return result.get("resources", []) if result else []

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a tool via tools/call method.

        Args:
            name: The name of the tool to call.
            arguments: Optional arguments for the tool.

        Returns:
            The tool result.
        """
        result = await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        return result if result else {}

    async def __aenter__(self) -> MCPClient:
        """Enter async context manager."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager."""
        await self.disconnect()


# =============================================================================
# Standalone helper functions (used by MCP tools)
# =============================================================================


async def ensure_connected_client(client: MCPClient) -> MCPClient:
    """Ensure the MCP client is connected.

    Args:
        client: The MCP client to connect.

    Returns:
        The connected client.
    """
    if client.state != MCPClientState.CONNECTED:
        await client.connect()
    return client


async def fetch_resources_for_client(client: MCPClient) -> list[dict[str, Any]]:
    """Fetch resources from an MCP client.

    Args:
        client: The connected MCP client.

    Returns:
        List of resources from the client.
    """
    return await client.list_resources()
