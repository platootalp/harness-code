"""
Tests for bridge/messaging.py.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest
from claude_code.bridge.messaging import (
    BoundedUUIDSet,
    ServerControlRequestHandlers,
    _make_control_response,
    _normalize_control_message_keys,
    _parse_json,
    handle_ingress_message,
    handle_server_control_request,
    is_eligible_bridge_message,
    is_sdk_control_request,
    is_sdk_control_response,
    is_sdk_message,
    make_result_message,
)


class MockMessage:
    """Mock Message for testing."""

    def __init__(
        self,
        msg_type: str = "user",
        is_virtual: bool = False,
        subtype: str | None = None,
    ):
        self.type = msg_type
        self.is_virtual = is_virtual
        self.subtype = subtype


class TestTypeGuards:
    """Tests for type guard functions."""

    def test_is_sdk_message_valid(self) -> None:
        """Test is_sdk_message with valid message."""
        msg = {"type": "user", "content": "hello"}
        assert is_sdk_message(msg) is True

    def test_is_sdk_message_null(self) -> None:
        """Test is_sdk_message with None."""
        assert is_sdk_message(None) is False

    def test_is_sdk_message_string_type(self) -> None:
        """Test is_sdk_message with non-dict."""
        assert is_sdk_message("not a dict") is False

    def test_is_sdk_message_missing_type(self) -> None:
        """Test is_sdk_message with missing type field."""
        assert is_sdk_message({"content": "hello"}) is False

    def test_is_sdk_message_non_string_type(self) -> None:
        """Test is_sdk_message with non-string type."""
        assert is_sdk_message({"type": 123}) is False

    def test_is_sdk_control_response_valid(self) -> None:
        """Test is_sdk_control_response with valid response."""
        msg = {"type": "control_response", "response": {"subtype": "success"}}
        assert is_sdk_control_response(msg) is True

    def test_is_sdk_control_response_wrong_type(self) -> None:
        """Test is_sdk_control_response with wrong type."""
        msg = {"type": "user", "response": {}}
        assert is_sdk_control_response(msg) is False

    def test_is_sdk_control_response_missing_response(self) -> None:
        """Test is_sdk_control_response with missing response."""
        msg = {"type": "control_response"}
        assert is_sdk_control_response(msg) is False

    def test_is_sdk_control_request_valid(self) -> None:
        """Test is_sdk_control_request with valid request."""
        msg = {
            "type": "control_request",
            "request_id": "123",
            "request": {"subtype": "initialize"},
        }
        assert is_sdk_control_request(msg) is True

    def test_is_sdk_control_request_missing_request_id(self) -> None:
        """Test is_sdk_control_request with missing request_id."""
        msg = {"type": "control_request", "request": {}}
        assert is_sdk_control_request(msg) is False

    def test_is_sdk_control_request_missing_request(self) -> None:
        """Test is_sdk_control_request with missing request."""
        msg = {"type": "control_request", "request_id": "123"}
        assert is_sdk_control_request(msg) is False

    def test_is_eligible_bridge_message_user(self) -> None:
        """Test is_eligible_bridge_message for user messages."""
        msg = MockMessage(msg_type="user")
        assert is_eligible_bridge_message(msg) is True

    def test_is_eligible_bridge_message_assistant(self) -> None:
        """Test is_eligible_bridge_message for assistant messages."""
        msg = MockMessage(msg_type="assistant")
        assert is_eligible_bridge_message(msg) is True

    def test_is_eligible_bridge_message_virtual(self) -> None:
        """Test is_eligible_bridge_message for virtual messages."""
        msg = MockMessage(msg_type="user", is_virtual=True)
        assert is_eligible_bridge_message(msg) is False

    def test_is_eligible_bridge_message_system_local_command(self) -> None:
        """Test is_eligible_bridge_message for system local_command."""
        msg = MockMessage(msg_type="system", subtype="local_command")
        assert is_eligible_bridge_message(msg) is True

    def test_is_eligible_bridge_message_system_other(self) -> None:
        """Test is_eligible_bridge_message for system non-local_command."""
        msg = MockMessage(msg_type="system", subtype="other")
        assert is_eligible_bridge_message(msg) is False


class TestParseHelpers:
    """Tests for parsing helper functions."""

    def test_parse_json_valid(self) -> None:
        """Test parsing valid JSON."""
        result = _parse_json('{"type": "user"}')
        assert result == {"type": "user"}

    def test_parse_json_invalid(self) -> None:
        """Test parsing invalid JSON returns None."""
        assert _parse_json("not json") is None

    def test_parse_json_empty(self) -> None:
        """Test parsing empty string returns None."""
        assert _parse_json("") is None

    def test_normalize_control_message_keys(self) -> None:
        """Test normalizing camelCase keys to snake_case."""
        data = {
            "requestId": "123",
            "sessionId": "sess_abc",
            "maxThinkingTokens": 1000,
            "nested": {
                "controlRequest": {"subtype": "init"},
            },
        }
        result = _normalize_control_message_keys(data)
        assert result["request_id"] == "123"
        assert result["session_id"] == "sess_abc"
        assert result["max_thinking_tokens"] == 1000
        assert result["nested"]["control_request"]["subtype"] == "init"

    def test_normalize_control_message_keys_non_dict(self) -> None:
        """Test normalizing non-dict returns as-is."""
        assert _normalize_control_message_keys("string") == "string"
        assert _normalize_control_message_keys(123) == 123


class TestBoundedUUIDSet:
    """Tests for BoundedUUIDSet ring buffer."""

    def test_add_and_has(self) -> None:
        """Test adding and checking UUIDs."""
        s = BoundedUUIDSet(capacity=3)
        s.add("uuid-1")
        assert s.has("uuid-1") is True
        assert s.has("uuid-2") is False

    def test_add_duplicate_ignored(self) -> None:
        """Test that duplicate UUIDs are ignored."""
        s = BoundedUUIDSet(capacity=3)
        s.add("uuid-1")
        s.add("uuid-1")  # Should not increase count
        assert s.has("uuid-1") is True

    def test_eviction(self) -> None:
        """Test that oldest entries are evicted."""
        s = BoundedUUIDSet(capacity=3)
        s.add("uuid-1")
        s.add("uuid-2")
        s.add("uuid-3")
        s.add("uuid-4")  # Should evict uuid-1
        assert s.has("uuid-1") is False
        assert s.has("uuid-2") is True
        assert s.has("uuid-3") is True
        assert s.has("uuid-4") is True

    def test_clear(self) -> None:
        """Test clearing the set."""
        s = BoundedUUIDSet(capacity=3)
        s.add("uuid-1")
        s.add("uuid-2")
        s.clear()
        assert s.has("uuid-1") is False
        assert s.has("uuid-2") is False

    def test_capacity_1(self) -> None:
        """Test capacity of 1."""
        s = BoundedUUIDSet(capacity=1)
        s.add("uuid-1")
        assert s.has("uuid-1") is True
        s.add("uuid-2")
        assert s.has("uuid-1") is False
        assert s.has("uuid-2") is True


class TestIngressRouting:
    """Tests for ingress message handling."""

    def test_routes_user_message(self) -> None:
        """Test that user messages are routed to on_inbound_message."""
        received: list[dict[str, Any]] = []

        def on_inbound(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_inbound = BoundedUUIDSet()

        data = json.dumps({"type": "user", "content": "hello", "uuid": "test-uuid"})
        handle_ingress_message(
            data, uuids_posted, uuids_inbound, on_inbound
        )

        assert len(received) == 1
        assert received[0]["content"] == "hello"

    def test_ignores_echo(self) -> None:
        """Test that messages in recentPostedUUIDs are ignored."""
        received: list[dict[str, Any]] = []

        def on_inbound(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_posted.add("echo-uuid")
        uuids_inbound = BoundedUUIDSet()

        data = json.dumps({"type": "user", "content": "echo", "uuid": "echo-uuid"})
        handle_ingress_message(
            data, uuids_posted, uuids_inbound, on_inbound
        )

        assert len(received) == 0

    def test_ignores_non_user(self) -> None:
        """Test that non-user messages are ignored."""
        received: list[dict[str, Any]] = []

        def on_inbound(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_inbound = BoundedUUIDSet()

        data = json.dumps({"type": "assistant", "content": "response"})
        handle_ingress_message(
            data, uuids_posted, uuids_inbound, on_inbound
        )

        assert len(received) == 0

    def test_routes_control_response(self) -> None:
        """Test that control_response is routed to on_permission_response."""
        received: list[dict[str, Any]] = []

        def on_response(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_inbound = BoundedUUIDSet()

        data = json.dumps({
            "type": "control_response",
            "response": {"subtype": "success"},
        })
        handle_ingress_message(
            data, uuids_posted, uuids_inbound, None, on_response
        )

        assert len(received) == 1

    def test_routes_control_request(self) -> None:
        """Test that control_request is routed to on_control_request."""
        received: list[dict[str, Any]] = []

        def on_request(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_inbound = BoundedUUIDSet()

        data = json.dumps({
            "type": "control_request",
            "request_id": "123",
            "request": {"subtype": "initialize"},
        })
        handle_ingress_message(
            data, uuids_posted, uuids_inbound, None, None, on_request
        )

        assert len(received) == 1
        assert received[0]["request"]["subtype"] == "initialize"

    def test_adds_uuid_to_inbound_set(self) -> None:
        """Test that user message UUIDs are added to recentInboundUUIDs."""
        received: list[dict[str, Any]] = []

        def on_inbound(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_inbound = BoundedUUIDSet()

        data = json.dumps({"type": "user", "uuid": "new-uuid"})
        handle_ingress_message(
            data, uuids_posted, uuids_inbound, on_inbound
        )

        assert uuids_inbound.has("new-uuid") is True

    def test_ignores_invalid_json(self) -> None:
        """Test that invalid JSON is silently ignored."""
        received: list[dict[str, Any]] = []

        def on_inbound(msg: dict[str, Any]) -> None:
            received.append(msg)

        uuids_posted = BoundedUUIDSet()
        uuids_inbound = BoundedUUIDSet()

        handle_ingress_message(
            "not valid json", uuids_posted, uuids_inbound, on_inbound
        )

        assert len(received) == 0


class TestServerControlRequest:
    """Tests for server control request handling."""

    def test_initialize_response(self) -> None:
        """Test initialize request returns capabilities."""
        written: list[dict[str, Any]] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "initialize"},
        }
        handle_server_control_request(request, handlers)

        assert len(written) == 1
        assert written[0]["type"] == "control_response"
        assert written[0]["response"]["subtype"] == "success"
        assert "pid" in written[0]["response"]["response"]

    def test_set_model_callback(self) -> None:
        """Test set_model calls on_set_model callback."""
        written: list[dict[str, Any]] = []
        models_set: list[str | None] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
            on_set_model=lambda m: models_set.append(m),
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "set_model", "model": "claude-3-5-sonnet"},
        }
        handle_server_control_request(request, handlers)

        assert models_set == ["claude-3-5-sonnet"]
        assert written[0]["response"]["subtype"] == "success"

    def test_interrupt_callback(self) -> None:
        """Test interrupt calls on_interrupt callback."""
        written: list[dict[str, Any]] = []
        interrupted: list[bool] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
            on_interrupt=lambda: interrupted.append(True),
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "interrupt"},
        }
        handle_server_control_request(request, handlers)

        assert interrupted == [True]
        assert written[0]["response"]["subtype"] == "success"

    def test_set_permission_mode_success(self) -> None:
        """Test set_permission_mode with successful callback."""
        written: list[dict[str, Any]] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
            on_set_permission_mode=lambda m: {"ok": True},
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "set_permission_mode", "mode": "auto"},
        }
        handle_server_control_request(request, handlers)

        assert written[0]["response"]["subtype"] == "success"

    def test_set_permission_mode_error(self) -> None:
        """Test set_permission_mode with error callback."""
        written: list[dict[str, Any]] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
            on_set_permission_mode=lambda m: {"ok": False, "error": "Not allowed"},
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "set_permission_mode", "mode": "auto"},
        }
        handle_server_control_request(request, handlers)

        assert written[0]["response"]["subtype"] == "error"
        assert written[0]["response"]["error"] == "Not allowed"

    def test_outbound_only_rejects_mutable(self) -> None:
        """Test outbound_only rejects non-initialize requests."""
        written: list[dict[str, Any]] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
            outbound_only=True,
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "set_model", "model": "claude-3-5-sonnet"},
        }
        handle_server_control_request(request, handlers)

        assert written[0]["response"]["subtype"] == "error"
        assert "outbound-only" in written[0]["response"]["error"]

    def test_outbound_only_allows_initialize(self) -> None:
        """Test outbound_only allows initialize request."""
        written: list[dict[str, Any]] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
            outbound_only=True,
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "initialize"},
        }
        handle_server_control_request(request, handlers)

        assert written[0]["response"]["subtype"] == "success"

    def test_unknown_subtype_returns_error(self) -> None:
        """Test unknown request subtype returns error."""
        written: list[dict[str, Any]] = []

        class MockTransport:
            def write(self, msg: dict[str, Any]) -> None:
                written.append(msg)

            def close(self) -> None:
                pass

        handlers = ServerControlRequestHandlers(
            transport=MockTransport(),  # type: ignore
            session_id="test-session",
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "unknown_subtype"},
        }
        handle_server_control_request(request, handlers)

        assert written[0]["response"]["subtype"] == "error"
        assert "unknown_subtype" in written[0]["response"]["error"]

    def test_no_transport_logs_and_returns(self) -> None:
        """Test that missing transport is handled gracefully."""
        handlers = ServerControlRequestHandlers(
            transport=None,
            session_id="test-session",
        )

        request = {
            "type": "control_request",
            "request_id": "req-123",
            "request": {"subtype": "initialize"},
        }
        # Should not raise
        handle_server_control_request(request, handlers)


class TestMakeResultMessage:
    """Tests for make_result_message."""

    def test_basic_fields(self) -> None:
        """Test basic fields of result message."""
        msg = make_result_message("session-abc")
        assert msg["type"] == "result"
        assert msg["subtype"] == "success"
        assert msg["session_id"] == "session-abc"
        assert msg["is_error"] is False
        assert msg["stop_reason"] is None
        assert msg["uuid"] is not None

    def test_usage_fields(self) -> None:
        """Test usage fields are present."""
        msg = make_result_message("session-abc")
        assert "usage" in msg
        assert msg["usage"]["input_tokens"] == 0
        assert msg["usage"]["output_tokens"] == 0

    def test_uuid_is_valid(self) -> None:
        """Test that UUID is valid format."""
        msg = make_result_message("session-abc")
        # Should not raise
        uuid.UUID(msg["uuid"])


class TestMakeControlResponse:
    """Tests for _make_control_response helper."""

    def test_basic_success(self) -> None:
        """Test basic success response."""
        resp = _make_control_response(
            session_id="sess-1",
            request_id="req-1",
            subtype="success",
        )
        assert resp["type"] == "control_response"
        assert resp["session_id"] == "sess-1"
        assert resp["response"]["subtype"] == "success"
        assert resp["response"]["request_id"] == "req-1"

    def test_error_response(self) -> None:
        """Test error response with error message."""
        resp = _make_control_response(
            session_id="sess-1",
            request_id="req-1",
            subtype="error",
            error="Something went wrong",
        )
        assert resp["response"]["subtype"] == "error"
        assert resp["response"]["error"] == "Something went wrong"

    def test_with_response_data(self) -> None:
        """Test response with additional data."""
        resp = _make_control_response(
            session_id="sess-1",
            request_id="req-1",
            subtype="success",
            response_data={"pid": 1234, "commands": []},
        )
        assert "response" in resp["response"]
        assert resp["response"]["response"]["pid"] == 1234
