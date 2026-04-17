"""MCP JSON-RPC protocol implementation.

TypeScript equivalent: src/services/mcp/protocol.ts
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MCPProtocolVersion(StrEnum):
    LATEST = "2024-11-05"


class MCPMessageType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPRequest:
    """JSON-RPC request."""

    method: str
    jsonrpc: str = "2.0"
    id: str | int | None = None
    params: dict[str, Any] | list[Any] | None = None


@dataclass
class MCPResponse:
    """JSON-RPC response."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: dict[str, Any] | list[Any] | None = None
    error: dict[str, Any] | None = None


class MCPProtocol:
    """MCP JSON-RPC protocol handler."""

    PROTOCOL_VERSION = "2024-11-05"

    def create_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        id: str | int | None = None,
    ) -> MCPRequest:
        """Create a JSON-RPC request.

        Args:
            method: The method name to call.
            params: Optional parameters for the method.
            id: Optional request ID (generated if not provided).

        Returns:
            MCPRequest instance.
        """
        return MCPRequest(
            jsonrpc="2.0",
            id=id,
            method=method,
            params=params,
        )

    def create_response(
        self,
        id: str | int | None,
        result: dict[str, Any] | list[Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> MCPResponse:
        """Create a JSON-RPC response.

        Args:
            id: The request ID this response corresponds to.
            result: The result data if successful.
            error: The error data if the request failed.

        Returns:
            MCPResponse instance.
        """
        return MCPResponse(
            jsonrpc="2.0",
            id=id,
            result=result,
            error=error,
        )

    def create_notification(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> MCPRequest:
        """Create a JSON-RPC notification (no response expected).

        Args:
            method: The method name to notify.
            params: Optional parameters for the method.

        Returns:
            MCPRequest instance with id=None.
        """
        return MCPRequest(
            jsonrpc="2.0",
            id=None,
            method=method,
            params=params,
        )

    def parse_message(
        self,
        data: str | bytes,
    ) -> MCPRequest | MCPResponse | None:
        """Parse a JSON-RPC message from string or bytes.

        Args:
            data: Raw JSON string or bytes.

        Returns:
            MCPRequest or MCPResponse instance, or None if parsing fails.
        """
        try:
            parsed = json.loads(data) if isinstance(data, bytes) else json.loads(data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        if not isinstance(parsed, dict):
            return None

        jsonrpc = parsed.get("jsonrpc")
        if jsonrpc != "2.0":
            return None

        # Determine if it's a request (with method) or response
        if "method" in parsed:
            return MCPRequest(
                jsonrpc=parsed.get("jsonrpc", "2.0"),
                id=parsed.get("id"),
                method=parsed.get("method", ""),
                params=parsed.get("params"),
            )
        else:
            return MCPResponse(
                jsonrpc=parsed.get("jsonrpc", "2.0"),
                id=parsed.get("id"),
                result=parsed.get("result"),
                error=parsed.get("error"),
            )

    def serialize_message(
        self,
        msg: MCPRequest | MCPResponse,
    ) -> bytes:
        """Serialize a JSON-RPC message to bytes.

        Args:
            msg: The message to serialize.

        Returns:
            UTF-8 encoded JSON bytes.
        """
        if isinstance(msg, MCPRequest):
            obj: dict[str, Any] = {
                "jsonrpc": msg.jsonrpc,
                "method": msg.method,
            }
            if msg.id is not None:
                obj["id"] = msg.id
            if msg.params is not None:
                obj["params"] = msg.params
        else:
            obj = {
                "jsonrpc": msg.jsonrpc,
            }
            if msg.id is not None:
                obj["id"] = msg.id
            if msg.result is not None:
                obj["result"] = msg.result
            if msg.error is not None:
                obj["error"] = msg.error

        return json.dumps(obj).encode("utf-8")

    @staticmethod
    def error_code_parse_error() -> dict[str, Any]:
        """Parse error (-32700): Invalid JSON was received."""
        return {"code": -32700, "message": "Parse error"}

    @staticmethod
    def error_code_invalid_request() -> dict[str, Any]:
        """Invalid Request (-32600): The JSON sent is not a valid Request object."""
        return {"code": -32600, "message": "Invalid Request"}

    @staticmethod
    def error_code_method_not_found() -> dict[str, Any]:
        """Method not found (-32601): The method does not exist/is not available."""
        return {"code": -32601, "message": "Method not found"}

    @staticmethod
    def error_code_invalid_params() -> dict[str, Any]:
        """Invalid params (-32602): Invalid method parameter(s)."""
        return {"code": -32602, "message": "Invalid params"}

    @staticmethod
    def error_code_internal_error() -> dict[str, Any]:
        """Internal error (-32603): Internal JSON-RPC error."""
        return {"code": -32603, "message": "Internal error"}
