"""Tests for services/mcp/protocol.py - MCPProtocol."""

from __future__ import annotations

import json

import pytest

from claude_code.services.mcp.protocol import (
    MCPProtocol,
    MCPProtocolVersion,
    MCPMessageType,
    MCPRequest,
    MCPResponse,
)


class TestMCPProtocolVersion:
    """Tests for MCPProtocolVersion enum."""

    def test_latest_version(self) -> None:
        """Test LATEST version is set correctly."""
        assert MCPProtocolVersion.LATEST == "2024-11-05"


class TestMCPMessageType:
    """Tests for MCPMessageType enum."""

    def test_all_types_exist(self) -> None:
        """Test all message types are defined."""
        assert MCPMessageType.REQUEST == "request"
        assert MCPMessageType.RESPONSE == "response"
        assert MCPMessageType.NOTIFICATION == "notification"
        assert MCPMessageType.ERROR == "error"


class TestMCPRequest:
    """Tests for MCPRequest dataclass."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        req = MCPRequest(method="tools/list")
        assert req.jsonrpc == "2.0"
        assert req.id is None
        assert req.method == "tools/list"
        assert req.params is None

    def test_with_params(self) -> None:
        """Test request with parameters."""
        req = MCPRequest(method="tools/call", params={"name": "test"}, id=1)
        assert req.method == "tools/call"
        assert req.params == {"name": "test"}
        assert req.id == 1


class TestMCPResponse:
    """Tests for MCPResponse dataclass."""

    def test_success_response(self) -> None:
        """Test successful response."""
        resp = MCPResponse(id=1, result={"tools": []})
        assert resp.jsonrpc == "2.0"
        assert resp.id == 1
        assert resp.result == {"tools": []}
        assert resp.error is None

    def test_error_response(self) -> None:
        """Test error response."""
        resp = MCPResponse(id=1, error={"code": -32600, "message": "Invalid Request"})
        assert resp.id == 1
        assert resp.error == {"code": -32600, "message": "Invalid Request"}
        assert resp.result is None


class TestMCPProtocol:
    """Tests for MCPProtocol class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.protocol = MCPProtocol()

    def test_protocol_version(self) -> None:
        """Test protocol version is set."""
        assert self.protocol.PROTOCOL_VERSION == "2024-11-05"

    def test_create_request_no_id(self) -> None:
        """Test creating request without ID."""
        req = self.protocol.create_request("tools/list")
        assert req.method == "tools/list"
        assert req.id is None
        assert req.params is None
        assert req.jsonrpc == "2.0"

    def test_create_request_with_params(self) -> None:
        """Test creating request with parameters."""
        params = {"name": "echo", "arguments": {"msg": "hello"}}
        req = self.protocol.create_request("tools/call", params, id=42)
        assert req.method == "tools/call"
        assert req.params == params
        assert req.id == 42

    def test_create_request_auto_id(self) -> None:
        """Test creating request with auto-generated ID."""
        req = self.protocol.create_request("ping", id=123)
        assert req.id == 123

    def test_create_response_success(self) -> None:
        """Test creating success response."""
        resp = self.protocol.create_response(1, result={"status": "ok"})
        assert resp.id == 1
        assert resp.result == {"status": "ok"}
        assert resp.error is None

    def test_create_response_error(self) -> None:
        """Test creating error response."""
        resp = self.protocol.create_response(
            1, error={"code": -32601, "message": "Method not found"}
        )
        assert resp.id == 1
        assert resp.result is None
        assert resp.error == {"code": -32601, "message": "Method not found"}

    def test_create_notification(self) -> None:
        """Test creating notification."""
        notif = self.protocol.create_notification("initialized", {})
        assert notif.method == "initialized"
        assert notif.params == {}
        assert notif.id is None
        assert notif.jsonrpc == "2.0"

    def test_parse_request_from_string(self) -> None:
        """Test parsing JSON-RPC request from string."""
        data = '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
        msg = self.protocol.parse_message(data)
        assert isinstance(msg, MCPRequest)
        assert msg.method == "tools/list"
        assert msg.id == 1
        assert msg.params == {}

    def test_parse_request_from_bytes(self) -> None:
        """Test parsing JSON-RPC request from bytes."""
        data = b'{"jsonrpc": "2.0", "id": 5, "method": "ping"}'
        msg = self.protocol.parse_message(data)
        assert isinstance(msg, MCPRequest)
        assert msg.method == "ping"
        assert msg.id == 5

    def test_parse_response_success(self) -> None:
        """Test parsing successful response."""
        data = '{"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}'
        msg = self.protocol.parse_message(data)
        assert isinstance(msg, MCPResponse)
        assert msg.id == 1
        assert msg.result == {"tools": []}
        assert msg.error is None

    def test_parse_response_error(self) -> None:
        """Test parsing error response."""
        data = '{"jsonrpc": "2.0", "id": 1, "error": {"code": -32600, "message": "Invalid"}}'
        msg = self.protocol.parse_message(data)
        assert isinstance(msg, MCPResponse)
        assert msg.id == 1
        assert msg.error == {"code": -32600, "message": "Invalid"}

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON returns None."""
        assert self.protocol.parse_message("not json") is None

    def test_parse_wrong_jsonrpc_version(self) -> None:
        """Test parsing wrong JSON-RPC version returns None."""
        data = '{"jsonrpc": "1.0", "method": "ping"}'
        assert self.protocol.parse_message(data) is None

    def test_parse_non_dict(self) -> None:
        """Test parsing non-dict returns None."""
        assert self.protocol.parse_message('"string"') is None
        assert self.protocol.parse_message("[1, 2, 3]") is None

    def test_parse_missing_method_or_result(self) -> None:
        """Test parsing dict without method or result returns Response."""
        data = '{"jsonrpc": "2.0", "id": 1, "result": {}}'
        msg = self.protocol.parse_message(data)
        assert isinstance(msg, MCPResponse)

    def test_serialize_request(self) -> None:
        """Test serializing request to bytes."""
        req = MCPRequest(jsonrpc="2.0", id=1, method="tools/list", params={})
        data = self.protocol.serialize_message(req)
        parsed = json.loads(data.decode())
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["method"] == "tools/list"
        assert parsed["params"] == {}

    def test_serialize_request_no_id(self) -> None:
        """Test serializing request without ID (notification)."""
        req = MCPRequest(jsonrpc="2.0", id=None, method="initialized", params={})
        data = self.protocol.serialize_message(req)
        parsed = json.loads(data.decode())
        assert parsed["method"] == "initialized"
        assert "id" not in parsed

    def test_serialize_request_no_params(self) -> None:
        """Test serializing request without params."""
        req = MCPRequest(jsonrpc="2.0", id=1, method="ping")
        data = self.protocol.serialize_message(req)
        parsed = json.loads(data.decode())
        assert "params" not in parsed

    def test_serialize_response_success(self) -> None:
        """Test serializing success response."""
        resp = MCPResponse(jsonrpc="2.0", id=1, result={"ok": True})
        data = self.protocol.serialize_message(resp)
        parsed = json.loads(data.decode())
        assert parsed["id"] == 1
        assert parsed["result"] == {"ok": True}
        assert "error" not in parsed

    def test_serialize_response_error(self) -> None:
        """Test serializing error response."""
        resp = MCPResponse(
            jsonrpc="2.0",
            id=1,
            result=None,
            error={"code": -32600, "message": "Invalid"},
        )
        data = self.protocol.serialize_message(resp)
        parsed = json.loads(data.decode())
        assert parsed["id"] == 1
        assert parsed["error"] == {"code": -32600, "message": "Invalid"}
        assert "result" not in parsed

    def test_error_codes(self) -> None:
        """Test standard JSON-RPC error codes."""
        assert self.protocol.error_code_parse_error() == {
            "code": -32700,
            "message": "Parse error",
        }
        assert self.protocol.error_code_invalid_request() == {
            "code": -32600,
            "message": "Invalid Request",
        }
        assert self.protocol.error_code_method_not_found() == {
            "code": -32601,
            "message": "Method not found",
        }
        assert self.protocol.error_code_invalid_params() == {
            "code": -32602,
            "message": "Invalid params",
        }
        assert self.protocol.error_code_internal_error() == {
            "code": -32603,
            "message": "Internal error",
        }
