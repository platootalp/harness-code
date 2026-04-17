"""IDE Bridge protocol.

TypeScript equivalent: src/bridge/types.ts, bridgeMessaging.ts

This module defines the message protocol for IDE bridge communication,
including message types, data structures, and serialization.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class BridgeMessageType(StrEnum):
    """Bridge message types for client-server communication."""

    # Client → Server
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

    # Server → Client
    CONTROL_REQUEST = "control_request"
    CONTROL_RESPONSE = "control_response"

    # Results
    RESULT = "result"


@dataclass
class BridgeMessage:
    """Message in the bridge protocol.

    Attributes:
        type: The message type (user, assistant, control_request, etc.).
        payload: The message payload data.
        id: Optional unique identifier for deduplication.
        version: Protocol version (default "1.0").
    """

    type: str
    payload: dict[str, Any]
    id: str | None = None
    version: str = "1.0"


@dataclass
class SDKControlRequest:
    """Server-initiated control requests.

    Used by the server to request the client to perform actions
    like initializing, setting model, etc.

    Attributes:
        subtype: The control request subtype (initialize, set_model, etc.).
        request_id: Unique identifier for this request.
        model: Model name for set_model subtype.
        max_thinking_tokens: Max thinking tokens for set_max_thinking_tokens.
        mode: Mode for set_mode subtype.
        tool_name: Tool name for tool_approve/reject subtypes.
        tool_input: Tool input data.
        tool_use_id: Tool use identifier.
    """

    subtype: str
    request_id: str | None = None
    model: str | None = None
    max_thinking_tokens: int | None = None
    mode: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None


@dataclass
class SDKControlResponse:
    """Client response to control requests.

    Attributes:
        subtype: Response type (success, error).
        request_id: The request ID this response corresponds to.
        response: Response data on success.
        error: Error message on failure.
    """

    subtype: str
    request_id: str
    response: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class BridgeProtocol:
    """Protocol for IDE bridge communication.

    Handles message serialization, deserialization, and factory methods
    for creating typed bridge messages.

    TypeScript equivalent: Message protocol in bridgeMessaging.ts

    Attributes:
        PROTOCOL_VERSION: Current protocol version string.
        _handlers: Registered message handlers by type.
    """

    PROTOCOL_VERSION: str = "1.0"

    _handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)

    def register_handler(self, message_type: str, handler: Callable[..., Any]) -> None:
        """Register a message handler for a specific message type.

        Args:
            message_type: The message type to handle.
            handler: Callback function to invoke for this message type.
        """
        self._handlers[message_type] = handler

    def parse_message(self, data: str | bytes) -> BridgeMessage | None:
        """Parse a message from JSON string or bytes.

        Args:
            data: Raw JSON data to parse.

        Returns:
            Parsed BridgeMessage, or None if parsing fails.
        """
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            parsed = json.loads(data)
            return BridgeMessage(
                type=parsed.get("type", ""),
                payload=parsed.get("payload", {}),
                id=parsed.get("id"),
                version=parsed.get("version", self.PROTOCOL_VERSION),
            )
        except json.JSONDecodeError:
            return None

    def serialize_message(self, message: BridgeMessage) -> bytes:
        """Serialize a BridgeMessage to JSON bytes.

        Args:
            message: The message to serialize.

        Returns:
            UTF-8 encoded JSON bytes.
        """
        data: dict[str, Any] = {
            "type": message.type,
            "payload": message.payload,
            "id": message.id,
            "version": message.version,
        }
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def create_user_message(
        self,
        content: str | list[dict[str, Any]],
        uuid: str | None = None,
    ) -> BridgeMessage:
        """Create a user message.

        Args:
            content: Message content (text string or content blocks).
            uuid: Optional unique identifier.

        Returns:
            A new BridgeMessage with type "user".
        """
        return BridgeMessage(
            type=BridgeMessageType.USER.value,
            payload={"message": {"content": content}},
            id=uuid,
        )

    def create_assistant_message(
        self,
        content: str | list[dict[str, Any]],
        uuid: str | None = None,
    ) -> BridgeMessage:
        """Create an assistant message.

        Args:
            content: Message content (text string or content blocks).
            uuid: Optional unique identifier.

        Returns:
            A new BridgeMessage with type "assistant".
        """
        return BridgeMessage(
            type=BridgeMessageType.ASSISTANT.value,
            payload={"message": {"content": content}},
            id=uuid,
        )

    def create_system_message(
        self,
        content: str,
        uuid: str | None = None,
    ) -> BridgeMessage:
        """Create a system message.

        Args:
            content: System message content.
            uuid: Optional unique identifier.

        Returns:
            A new BridgeMessage with type "system".
        """
        return BridgeMessage(
            type=BridgeMessageType.SYSTEM.value,
            payload={"message": {"content": content}},
            id=uuid,
        )

    def create_control_request(
        self,
        subtype: str,
        request_id: str | None = None,
        **kwargs: Any,
    ) -> BridgeMessage:
        """Create a control request message.

        Args:
            subtype: The control request subtype.
            request_id: Optional request identifier.
            **kwargs: Additional subtype-specific fields.

        Returns:
            A new BridgeMessage with type "control_request".
        """
        payload: dict[str, Any] = {"subtype": subtype}
        if request_id:
            payload["request_id"] = request_id
        payload.update(kwargs)
        return BridgeMessage(
            type=BridgeMessageType.CONTROL_REQUEST.value,
            payload=payload,
            id=request_id,
        )

    def create_control_response(
        self,
        subtype: str,
        request_id: str,
        response: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> BridgeMessage:
        """Create a control response message.

        Args:
            subtype: Response type (success, error).
            request_id: The request ID this responds to.
            response: Response data on success.
            error: Error message on failure.

        Returns:
            A new BridgeMessage with type "control_response".
        """
        payload: dict[str, Any] = {
            "subtype": subtype,
            "request_id": request_id,
        }
        if response:
            payload["response"] = response
        if error:
            payload["error"] = error
        return BridgeMessage(
            type=BridgeMessageType.CONTROL_RESPONSE.value,
            payload=payload,
            id=request_id,
        )

    def create_result_message(
        self,
        subtype: str,
        **kwargs: Any,
    ) -> BridgeMessage:
        """Create a result message.

        Args:
            subtype: Result subtype (success, error_max_turns, etc.).
            **kwargs: Additional result fields.

        Returns:
            A new BridgeMessage with type "result".
        """
        return BridgeMessage(
            type=BridgeMessageType.RESULT.value,
            payload={"subtype": subtype, **kwargs},
        )
