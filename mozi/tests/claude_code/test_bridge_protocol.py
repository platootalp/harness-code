"""
Tests for bridge/protocol.py - Bridge protocol types and serialization.
"""

from __future__ import annotations

import json

import pytest
from claude_code.bridge.protocol import (
    BridgeMessage,
    BridgeMessageType,
    BridgeProtocol,
    SDKControlRequest,
    SDKControlResponse,
)


class TestBridgeMessageType:
    """Tests for BridgeMessageType enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert BridgeMessageType.USER.value == "user"
        assert BridgeMessageType.ASSISTANT.value == "assistant"
        assert BridgeMessageType.SYSTEM.value == "system"
        assert BridgeMessageType.CONTROL_REQUEST.value == "control_request"
        assert BridgeMessageType.CONTROL_RESPONSE.value == "control_response"
        assert BridgeMessageType.RESULT.value == "result"

    def test_from_string(self) -> None:
        """Test creating from string value."""
        assert BridgeMessageType("user") == BridgeMessageType.USER
        assert BridgeMessageType("control_request") == BridgeMessageType.CONTROL_REQUEST


class TestBridgeMessage:
    """Tests for BridgeMessage dataclass."""

    def test_create_minimal(self) -> None:
        """Test creating with minimal fields."""
        msg = BridgeMessage(type="user", payload={})
        assert msg.type == "user"
        assert msg.payload == {}
        assert msg.id is None
        assert msg.version == "1.0"

    def test_create_full(self) -> None:
        """Test creating with all fields."""
        msg = BridgeMessage(
            type="assistant",
            payload={"content": "Hello"},
            id="msg-123",
            version="2.0",
        )
        assert msg.type == "assistant"
        assert msg.payload == {"content": "Hello"}
        assert msg.id == "msg-123"
        assert msg.version == "2.0"


class TestSDKControlRequest:
    """Tests for SDKControlRequest dataclass."""

    def test_create_minimal(self) -> None:
        """Test creating with minimal fields."""
        req = SDKControlRequest(subtype="initialize")
        assert req.subtype == "initialize"
        assert req.request_id is None
        assert req.model is None

    def test_create_full(self) -> None:
        """Test creating with all fields."""
        req = SDKControlRequest(
            subtype="set_model",
            request_id="req-456",
            model="claude-opus-4-6",
            max_thinking_tokens=10000,
            mode="auto",
            tool_name="bash",
            tool_input={"command": "ls"},
            tool_use_id="tool-789",
        )
        assert req.subtype == "set_model"
        assert req.request_id == "req-456"
        assert req.model == "claude-opus-4-6"
        assert req.max_thinking_tokens == 10000
        assert req.mode == "auto"
        assert req.tool_name == "bash"
        assert req.tool_input == {"command": "ls"}
        assert req.tool_use_id == "tool-789"


class TestSDKControlResponse:
    """Tests for SDKControlResponse dataclass."""

    def test_create_success(self) -> None:
        """Test creating a success response."""
        resp = SDKControlResponse(
            subtype="success",
            request_id="req-123",
            response={"status": "ok"},
        )
        assert resp.subtype == "success"
        assert resp.request_id == "req-123"
        assert resp.response == {"status": "ok"}
        assert resp.error is None

    def test_create_error(self) -> None:
        """Test creating an error response."""
        resp = SDKControlResponse(
            subtype="error",
            request_id="req-123",
            error="Invalid request",
        )
        assert resp.subtype == "error"
        assert resp.request_id == "req-123"
        assert resp.error == "Invalid request"
        assert resp.response is None


class TestBridgeProtocol:
    """Tests for BridgeProtocol class."""

    def test_protocol_version(self) -> None:
        """Test protocol version constant."""
        assert BridgeProtocol.PROTOCOL_VERSION == "1.0"

    def test_create_protocol(self) -> None:
        """Test creating a protocol instance."""
        protocol = BridgeProtocol()
        assert protocol.PROTOCOL_VERSION == "1.0"
        assert protocol._handlers == {}

    def test_register_handler(self) -> None:
        """Test registering a message handler."""
        protocol = BridgeProtocol()

        def handler(msg: BridgeMessage) -> None:
            pass

        protocol.register_handler("user", handler)
        assert "user" in protocol._handlers
        assert protocol._handlers["user"] is handler


class TestParseMessage:
    """Tests for parse_message method."""

    def test_parse_valid_json_string(self) -> None:
        """Test parsing valid JSON string."""
        protocol = BridgeProtocol()
        data = '{"type": "user", "payload": {"content": "hello"}, "id": "123"}'
        msg = protocol.parse_message(data)

        assert msg is not None
        assert msg.type == "user"
        assert msg.payload == {"content": "hello"}
        assert msg.id == "123"
        assert msg.version == "1.0"

    def test_parse_valid_bytes(self) -> None:
        """Test parsing valid JSON bytes."""
        protocol = BridgeProtocol()
        data = b'{"type": "assistant", "payload": {}}'
        msg = protocol.parse_message(data)

        assert msg is not None
        assert msg.type == "assistant"

    def test_parse_with_version(self) -> None:
        """Test parsing message with explicit version."""
        protocol = BridgeProtocol()
        data = '{"type": "user", "payload": {}, "version": "2.0"}'
        msg = protocol.parse_message(data)

        assert msg is not None
        assert msg.version == "2.0"

    def test_parse_missing_fields(self) -> None:
        """Test parsing JSON with missing fields uses defaults."""
        protocol = BridgeProtocol()
        data = '{"type": "user"}'
        msg = protocol.parse_message(data)

        assert msg is not None
        assert msg.type == "user"
        assert msg.payload == {}
        assert msg.id is None
        assert msg.version == "1.0"

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON returns None."""
        protocol = BridgeProtocol()
        msg = protocol.parse_message("not valid json")
        assert msg is None

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string returns None."""
        protocol = BridgeProtocol()
        msg = protocol.parse_message("")
        assert msg is None


class TestSerializeMessage:
    """Tests for serialize_message method."""

    def test_serialize_basic(self) -> None:
        """Test serializing a basic message."""
        protocol = BridgeProtocol()
        msg = BridgeMessage(
            type="user",
            payload={"content": "hello"},
            id="123",
        )
        data = protocol.serialize_message(msg)

        assert isinstance(data, bytes)
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["type"] == "user"
        assert parsed["payload"] == {"content": "hello"}
        assert parsed["id"] == "123"
        assert parsed["version"] == "1.0"

    def test_serialize_unicode(self) -> None:
        """Test serializing message with unicode content."""
        protocol = BridgeProtocol()
        msg = BridgeMessage(
            type="user",
            payload={"content": "Hello, \u4e16\u754c"},
        )
        data = protocol.serialize_message(msg)
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["payload"]["content"] == "Hello, \u4e16\u754c"

    def test_roundtrip(self) -> None:
        """Test serialize/parse roundtrip."""
        protocol = BridgeProtocol()
        original = BridgeMessage(
            type="assistant",
            payload={"message": {"content": ["Hello", "World"]}},
            id="msg-abc",
            version="1.0",
        )
        data = protocol.serialize_message(original)
        restored = protocol.parse_message(data)

        assert restored is not None
        assert restored.type == original.type
        assert restored.payload == original.payload
        assert restored.id == original.id
        assert restored.version == original.version


class TestCreateUserMessage:
    """Tests for create_user_message method."""

    def test_create_with_string(self) -> None:
        """Test creating user message with string content."""
        protocol = BridgeProtocol()
        msg = protocol.create_user_message("Hello", uuid="123")

        assert msg.type == "user"
        assert msg.payload == {"message": {"content": "Hello"}}
        assert msg.id == "123"

    def test_create_with_content_blocks(self) -> None:
        """Test creating user message with content blocks."""
        protocol = BridgeProtocol()
        content = [{"type": "text", "text": "Hello"}]
        msg = protocol.create_user_message(content, uuid="456")

        assert msg.type == "user"
        assert msg.payload == {"message": {"content": content}}
        assert msg.id == "456"

    def test_create_without_uuid(self) -> None:
        """Test creating user message without uuid."""
        protocol = BridgeProtocol()
        msg = protocol.create_user_message("Hello")

        assert msg.id is None


class TestCreateAssistantMessage:
    """Tests for create_assistant_message method."""

    def test_create_with_string(self) -> None:
        """Test creating assistant message."""
        protocol = BridgeProtocol()
        msg = protocol.create_assistant_message("Hi there", uuid="789")

        assert msg.type == "assistant"
        assert msg.payload == {"message": {"content": "Hi there"}}
        assert msg.id == "789"


class TestCreateSystemMessage:
    """Tests for create_system_message method."""

    def test_create(self) -> None:
        """Test creating system message."""
        protocol = BridgeProtocol()
        msg = protocol.create_system_message("System notification", uuid="sys-1")

        assert msg.type == "system"
        assert msg.payload == {"message": {"content": "System notification"}}


class TestCreateControlRequest:
    """Tests for create_control_request method."""

    def test_create_initialize(self) -> None:
        """Test creating initialize control request."""
        protocol = BridgeProtocol()
        msg = protocol.create_control_request(
            subtype="initialize",
            request_id="req-1",
        )

        assert msg.type == "control_request"
        assert msg.payload["subtype"] == "initialize"
        assert msg.payload["request_id"] == "req-1"

    def test_create_with_model(self) -> None:
        """Test creating set_model control request."""
        protocol = BridgeProtocol()
        msg = protocol.create_control_request(
            subtype="set_model",
            request_id="req-2",
            model="claude-opus-4-6",
        )

        assert msg.payload["model"] == "claude-opus-4-6"


class TestCreateControlResponse:
    """Tests for create_control_response method."""

    def test_create_success(self) -> None:
        """Test creating success control response."""
        protocol = BridgeProtocol()
        msg = protocol.create_control_response(
            subtype="success",
            request_id="req-1",
            response={"initialized": True},
        )

        assert msg.type == "control_response"
        assert msg.payload["subtype"] == "success"
        assert msg.payload["request_id"] == "req-1"
        assert msg.payload["response"] == {"initialized": True}

    def test_create_error(self) -> None:
        """Test creating error control response."""
        protocol = BridgeProtocol()
        msg = protocol.create_control_response(
            subtype="error",
            request_id="req-2",
            error="Failed to set model",
        )

        assert msg.type == "control_response"
        assert msg.payload["subtype"] == "error"
        assert msg.payload["error"] == "Failed to set model"


class TestCreateResultMessage:
    """Tests for create_result_message method."""

    def test_create_success(self) -> None:
        """Test creating success result message."""
        protocol = BridgeProtocol()
        msg = protocol.create_result_message(subtype="success")

        assert msg.type == "result"
        assert msg.payload["subtype"] == "success"

    def test_create_error_max_turns(self) -> None:
        """Test creating max_turns result message."""
        protocol = BridgeProtocol()
        msg = protocol.create_result_message(
            subtype="error_max_turns",
            turns=10,
        )

        assert msg.type == "result"
        assert msg.payload["subtype"] == "error_max_turns"
        assert msg.payload["turns"] == 10
