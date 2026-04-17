"""Ingress message handler for bridge connections.

Routes incoming bridge messages by type to registered callbacks.
Provides a high-level interface over the lower-level handle_ingress_message
function from messaging.py.

TypeScript equivalent: src/bridge/messageHandler.ts (conceptually)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .messaging import BoundedUUIDSet, handle_ingress_message

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# Type Aliases
# =============================================================================

SDKMessage = dict[str, Any]
SDKControlRequest = dict[str, Any]
SDKControlResponse = dict[str, Any]

# Callback signatures
OnUserMessage = Callable[[SDKMessage], None]
OnAssistantMessage = Callable[[SDKMessage], None]
OnControlRequest = Callable[[SDKControlRequest], None]
OnControlResponse = Callable[[SDKControlResponse], None]
OnResult = Callable[[dict[str, Any]], None]
OnRawMessage = Callable[[str, dict[str, Any] | None], None]


# =============================================================================
# IngressMessageHandler
# =============================================================================


@dataclass
class IngressMessageHandler:
    """Routes incoming bridge messages by type to registered callbacks.

    This handler wraps the lower-level handle_ingress_message function,
    providing callback-based routing for each message type. It maintains
    its own BoundedUUIDSet instances for echo detection and dedup.

    TypeScript equivalent: Message routing in replBridge.ts (handleIngressMessage)

    Attributes:
        on_user_message: Callback for incoming user messages.
        on_assistant_message: Callback for assistant messages.
        on_control_request: Callback for server-initiated control requests.
        on_control_response: Callback for permission responses.
        on_result: Callback for result messages.
        on_raw: Optional callback for all raw messages before routing.
        echo_dedup_capacity: Capacity of the echo-detection UUID set.
        inbound_dedup_capacity: Capacity of the inbound-dedup UUID set.
    """

    on_user_message: OnUserMessage | None = None
    on_assistant_message: OnAssistantMessage | None = None
    on_control_request: OnControlRequest | None = None
    on_control_response: OnControlResponse | None = None
    on_result: OnResult | None = None
    on_raw: OnRawMessage | None = None

    # Internal dedup sets
    _recent_posted_uuids: BoundedUUIDSet = field(
        default_factory=lambda: BoundedUUIDSet(2000)
    )
    _recent_inbound_uuids: BoundedUUIDSet = field(
        default_factory=lambda: BoundedUUIDSet(2000)
    )

    def handle(self, data: str | bytes) -> None:
        """Parse and route an ingress message.

        Args:
            data: Raw message data (JSON string or bytes).
        """
        data_str = data.decode("utf-8") if isinstance(data, bytes) else data

        # Fire raw callback first
        if self.on_raw:
            parsed = self._try_parse(data_str)
            self.on_raw(data_str, parsed)

        # Route through the lower-level handler
        def on_inbound(msg: SDKMessage) -> None:
            if self.on_user_message:
                self.on_user_message(msg)

        def on_permission_response(msg: SDKControlResponse) -> None:
            if self.on_control_response:
                self.on_control_response(msg)

        def on_control(req: SDKControlRequest) -> None:
            if self.on_control_request:
                self.on_control_request(req)

        handle_ingress_message(
            data=data_str,
            recent_posted_uuids=self._recent_posted_uuids,
            recent_inbound_uuids=self._recent_inbound_uuids,
            on_inbound_message=on_inbound,  # type: ignore[arg-type]
            on_permission_response=on_permission_response,
            on_control_request=on_control,
        )

    def _try_parse(self, data: str) -> dict[str, Any] | None:
        """Attempt to parse JSON data.

        Args:
            data: JSON string to parse.

        Returns:
            Parsed dict, or None on failure.
        """
        try:
            return dict[str, Any](json.loads(data))
        except (json.JSONDecodeError, TypeError):
            return None

    def add_posted_uuid(self, uuid_str: str) -> None:
        """Add a UUID to the echo-detection set.

        Call this when sending messages so echoed copies are ignored.

        Args:
            uuid_str: The UUID of a sent message.
        """
        self._recent_posted_uuids.add(uuid_str)

    def has_posted_uuid(self, uuid_str: str) -> bool:
        """Check if a UUID is in the echo-detection set.

        Args:
            uuid_str: The UUID to check.

        Returns:
            True if the UUID is present (message was sent by us).
        """
        return self._recent_posted_uuids.has(uuid_str)

    def clear_dedup_sets(self) -> None:
        """Clear both dedup sets."""
        self._recent_posted_uuids.clear()
        self._recent_inbound_uuids.clear()


# =============================================================================
# Factory Function
# =============================================================================


def create_ingress_handler(
    on_user: OnUserMessage | None = None,
    on_assistant: OnAssistantMessage | None = None,
    on_control_request: OnControlRequest | None = None,
    on_control_response: OnControlResponse | None = None,
    on_result: OnResult | None = None,
    on_raw: OnRawMessage | None = None,
) -> IngressMessageHandler:
    """Create an IngressMessageHandler with the given callbacks.

    Convenience factory for creating a handler with specific callbacks.

    Args:
        on_user: Callback for user messages.
        on_assistant: Callback for assistant messages.
        on_control_request: Callback for control requests.
        on_control_response: Callback for control responses.
        on_result: Callback for result messages.
        on_raw: Optional raw callback for all messages.

    Returns:
        A configured IngressMessageHandler.
    """
    return IngressMessageHandler(
        on_user_message=on_user,
        on_assistant_message=on_assistant,
        on_control_request=on_control_request,
        on_control_response=on_control_response,
        on_result=on_result,
        on_raw=on_raw,
    )
