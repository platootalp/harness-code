"""
Tests for bridge/handler.py - Ingress message handler.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


class TestIngressMessageHandler:
    """Tests for IngressMessageHandler."""

    def test_create_with_defaults(self) -> None:
        """Handler can be created with no callbacks."""
        from claude_code.bridge.handler import IngressMessageHandler

        handler = IngressMessageHandler()
        assert handler.on_user_message is None
        assert handler.on_assistant_message is None
        assert handler.on_control_request is None
        assert handler.on_control_response is None
        assert handler.on_result is None
        assert handler.on_raw is None

    def test_create_with_callbacks(self) -> None:
        """Handler can be created with all callbacks."""
        from claude_code.bridge.handler import IngressMessageHandler

        def on_user(msg: dict[str, Any]) -> None:
            pass

        def on_assistant(msg: dict[str, Any]) -> None:
            pass

        def on_control(req: dict[str, Any]) -> None:
            pass

        def on_response(resp: dict[str, Any]) -> None:
            pass

        def on_result(result: dict[str, Any]) -> None:
            pass

        def on_raw(data: str, parsed: dict[str, Any] | None) -> None:
            pass

        handler = IngressMessageHandler(
            on_user_message=on_user,
            on_assistant_message=on_assistant,
            on_control_request=on_control,
            on_control_response=on_response,
            on_result=on_result,
            on_raw=on_raw,
        )
        assert handler.on_user_message is on_user
        assert handler.on_assistant_message is on_assistant
        assert handler.on_control_request is on_control
        assert handler.on_control_response is on_response
        assert handler.on_result is on_result
        assert handler.on_raw is on_raw

    def test_add_posted_uuid(self) -> None:
        """UUIDs can be added to echo detection set."""
        from claude_code.bridge.handler import IngressMessageHandler

        handler = IngressMessageHandler()
        handler.add_posted_uuid("uuid-123")
        assert handler.has_posted_uuid("uuid-123") is True
        assert handler.has_posted_uuid("uuid-456") is False

    def test_clear_dedup_sets(self) -> None:
        """Dedup sets can be cleared."""
        from claude_code.bridge.handler import IngressMessageHandler

        handler = IngressMessageHandler()
        handler.add_posted_uuid("uuid-123")
        handler.clear_dedup_sets()
        assert handler.has_posted_uuid("uuid-123") is False


class TestIngressMessageHandlerHandle:
    """Tests for handler.handle() method."""

    def test_handle_raw_callback(self) -> None:
        """Raw callback is fired with data and parsed message."""
        from claude_code.bridge.handler import IngressMessageHandler

        raw_calls: list[tuple[str, dict[str, Any] | None]] = []

        def on_raw(data: str, parsed: dict[str, Any] | None) -> None:
            raw_calls.append((data, parsed))

        handler = IngressMessageHandler(on_raw=on_raw)
        handler.handle('{"type": "user", "content": "hello"}')

        assert len(raw_calls) == 1
        assert raw_calls[0][0] == '{"type": "user", "content": "hello"}'
        assert raw_calls[0][1] == {"type": "user", "content": "hello"}

    def test_handle_raw_callback_with_invalid_json(self) -> None:
        """Raw callback handles invalid JSON gracefully."""
        from claude_code.bridge.handler import IngressMessageHandler

        raw_calls: list[tuple[str, dict[str, Any] | None]] = []

        def on_raw(data: str, parsed: dict[str, Any] | None) -> None:
            raw_calls.append((data, parsed))

        handler = IngressMessageHandler(on_raw=on_raw)
        handler.handle("not valid json{")

        assert len(raw_calls) == 1
        assert raw_calls[0][0] == "not valid json{"
        assert raw_calls[0][1] is None

    def test_handle_bytes_input(self) -> None:
        """Handler accepts bytes input and decodes to string."""
        from claude_code.bridge.handler import IngressMessageHandler

        raw_calls: list[tuple[str, dict[str, Any] | None]] = []

        def on_raw(data: str, parsed: dict[str, Any] | None) -> None:
            raw_calls.append((data, parsed))

        handler = IngressMessageHandler(on_raw=on_raw)
        handler.handle(b'{"type": "user", "content": "hello"}')

        assert len(raw_calls) == 1
        assert raw_calls[0][0] == '{"type": "user", "content": "hello"}'

    def test_handle_user_message_callback(self) -> None:
        """User message callback is fired for user messages."""
        from claude_code.bridge.handler import IngressMessageHandler

        user_messages: list[dict[str, Any]] = []

        def on_user(msg: dict[str, Any]) -> None:
            user_messages.append(msg)

        handler = IngressMessageHandler(on_user_message=on_user)
        handler.handle('{"type": "user", "content": "hello"}')

        assert len(user_messages) == 1
        assert user_messages[0]["type"] == "user"
        assert user_messages[0]["content"] == "hello"


class TestCreateIngressHandler:
    """Tests for create_ingress_handler factory."""

    def test_factory_creates_handler(self) -> None:
        """Factory creates handler with correct callbacks."""
        from claude_code.bridge.handler import create_ingress_handler

        def on_user(msg: dict[str, Any]) -> None:
            pass

        handler = create_ingress_handler(on_user=on_user)
        assert handler.on_user_message is on_user

    def test_factory_with_all_callbacks(self) -> None:
        """Factory creates handler with all callback types."""
        from claude_code.bridge.handler import create_ingress_handler

        callbacks = {
            "on_user": MagicMock(),
            "on_assistant": MagicMock(),
            "on_control_request": MagicMock(),
            "on_control_response": MagicMock(),
            "on_result": MagicMock(),
            "on_raw": MagicMock(),
        }

        handler = create_ingress_handler(
            on_user=callbacks["on_user"],
            on_assistant=callbacks["on_assistant"],
            on_control_request=callbacks["on_control_request"],
            on_control_response=callbacks["on_control_response"],
            on_result=callbacks["on_result"],
            on_raw=callbacks["on_raw"],
        )

        assert handler.on_user_message is callbacks["on_user"]
        assert handler.on_assistant_message is callbacks["on_assistant"]
        assert handler.on_control_request is callbacks["on_control_request"]
        assert handler.on_control_response is callbacks["on_control_response"]
        assert handler.on_result is callbacks["on_result"]
        assert handler.on_raw is callbacks["on_raw"]


class TestTypeAliases:
    """Tests for type aliases."""

    def test_sdk_message_type(self) -> None:
        """SDKMessage is a dict type."""
        from claude_code.bridge.handler import SDKMessage

        msg: SDKMessage = {"type": "user", "content": "hello"}
        assert msg["type"] == "user"

    def test_callback_signatures(self) -> None:
        """Callback type aliases are callable."""
        from claude_code.bridge.handler import (
            OnAssistantMessage,
            OnControlRequest,
            OnControlResponse,
            OnRawMessage,
            OnResult,
            OnUserMessage,
        )

        def on_user(msg: dict[str, Any]) -> None:
            pass

        def on_assistant(msg: dict[str, Any]) -> None:
            pass

        def on_control(req: dict[str, Any]) -> None:
            pass

        def on_response(resp: dict[str, Any]) -> None:
            pass

        def on_result(result: dict[str, Any]) -> None:
            pass

        def on_raw(data: str, parsed: dict[str, Any] | None) -> None:
            pass

        # These should type-check (if mypy were running on tests)
        _user: OnUserMessage = on_user
        _assistant: OnAssistantMessage = on_assistant
        _control: OnControlRequest = on_control
        _response: OnControlResponse = on_response
        _result: OnResult = on_result
        _raw: OnRawMessage = on_raw

        assert _user is on_user
        assert _assistant is on_assistant
        assert _control is on_control
        assert _response is on_response
        assert _result is on_result
        assert _raw is on_raw
