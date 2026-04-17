"""
Bridge messaging module.

Shared transport-layer helpers for bridge message handling.

Extracted from replBridge so both the env-based core and the env-less core
can use the same ingress parsing, control-request handling, and echo-dedup
machinery.

TypeScript equivalent: src/bridge/bridgeMessaging.ts
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ..models.message import Message


# =============================================================================
# Type Aliases
# =============================================================================

SDKMessage = dict[str, Any]
SDKControlRequest = dict[str, Any]
SDKControlResponse = dict[str, Any]


# =============================================================================
# Type Guards
# =============================================================================


def is_sdk_message(value: object | None) -> bool:
    """Type guard for parsed WebSocket messages.

    SDKMessage is a discriminated union on 'type' — validating the
    discriminant is sufficient for the predicate.

    Args:
        value: The value to check.

    Returns:
        True if value is an SDKMessage.
    """
    return (
        value is not None
        and isinstance(value, dict)
        and "type" in value
        and isinstance(value["type"], str)
    )


def is_sdk_control_response(value: object | None) -> bool:
    """Type guard for control_response messages from the server.

    Args:
        value: The value to check.

    Returns:
        True if value is an SDKControlResponse.
    """
    return (
        value is not None
        and isinstance(value, dict)
        and value.get("type") == "control_response"
        and "response" in value
    )


def is_sdk_control_request(value: object | None) -> bool:
    """Type guard for control_request messages from the server.

    Args:
        value: The value to check.

    Returns:
        True if value is an SDKControlRequest.
    """
    return (
        value is not None
        and isinstance(value, dict)
        and value.get("type") == "control_request"
        and "request_id" in value
        and "request" in value
    )


def is_eligible_bridge_message(m: Message) -> bool:
    """Check if a message type should be forwarded to the bridge transport.

    The server only wants user/assistant turns and slash-command system events;
    everything else (tool_result, progress, etc.) is internal REPL chatter.

    Args:
        m: The message to check.

    Returns:
        True if the message should be forwarded.
    """
    # Virtual messages (REPL inner calls) are display-only
    msg_type = getattr(m, "type", None)
    is_virtual = getattr(m, "is_virtual", False)

    if (msg_type in ("user", "assistant")) and is_virtual:
        return False

    return msg_type in ("user", "assistant") or (
        msg_type == "system" and getattr(m, "subtype", None) == "local_command"
    )


# =============================================================================
# Ingress Routing
# =============================================================================


# Callback types for ingress handling
OnInboundMessage = Callable[["Message"], None]
OnPermissionResponse = Callable[[SDKControlResponse], None]
OnControlRequest = Callable[[SDKControlRequest], None]


def _log_for_debugging(message: str) -> None:
    """Log a debug message if debugging is enabled."""
    if os.environ.get("CLAUDE_CODE_BRIDGE_DEBUG"):
        print(f"[bridge:repl] {message}", flush=True)


def _parse_json(data: str) -> Any:
    """Parse JSON string, returning None on failure."""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


def _normalize_control_message_keys(data: Any) -> Any:
    """Normalize control message keys to snake_case.

    The server may send camelCase or mixed keys; normalize them
    to the snake_case form used internally.

    Args:
        data: The parsed JSON data.

    Returns:
        Data with normalized keys.
    """
    if not isinstance(data, dict):
        return data

    # Common key mappings from camelCase to snake_case
    KEY_MAP = {
        "requestId": "request_id",
        "sessionId": "session_id",
        "controlRequest": "control_request",
        "controlResponse": "control_response",
        "maxThinkingTokens": "max_thinking_tokens",
        "permissionMode": "permission_mode",
        "isError": "is_error",
        "numTurns": "num_turns",
        "totalCostUsd": "total_cost_usd",
        "modelUsage": "model_usage",
        "permissionDenials": "permission_denials",
        "availableOutputStyles": "available_output_styles",
    }

    result: dict[str, Any] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            result[str(key)] = value
            continue
        new_key = KEY_MAP.get(key, key)
        if isinstance(value, dict):
            result[new_key] = _normalize_control_message_keys(value)
        elif isinstance(value, list):
            result[new_key] = [
                _normalize_control_message_keys(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[new_key] = value
    return result


def handle_ingress_message(
    data: str,
    recent_posted_uuids: BoundedUUIDSet,
    recent_inbound_uuids: BoundedUUIDSet,
    on_inbound_message: OnInboundMessage | None,
    on_permission_response: OnPermissionResponse | None = None,
    on_control_request: OnControlRequest | None = None,
) -> None:
    """Parse an ingress WebSocket message and route it to the appropriate handler.

    Ignores messages whose UUID is in recentPostedUUIDs (echoes of what we sent)
    or in recentInboundUUIDs (re-deliveries we've already forwarded).

    Args:
        data: Raw WebSocket message data.
        recent_posted_uuids: UUIDs we've sent (for echo detection).
        recent_inbound_uuids: UUIDs we've already forwarded (for dedup).
        on_inbound_message: Callback for inbound user messages.
        on_permission_response: Callback for permission responses.
        on_control_request: Callback for control requests from server.
    """
    try:
        parsed = _normalize_control_message_keys(_parse_json(data))
        if parsed is None:
            return

        # control_response is not an SDKMessage — check before type guard
        if is_sdk_control_response(parsed):
            _log_for_debugging("Ingress message type=control_response")
            if on_permission_response:
                on_permission_response(parsed)
            return

        # control_request from the server (initialize, set_model, can_use_tool)
        if is_sdk_control_request(parsed):
            _log_for_debugging(
                f"Inbound control_request subtype={parsed.get('request', {}).get('subtype', 'unknown')}"
            )
            if on_control_request:
                on_control_request(parsed)
            return

        if not is_sdk_message(parsed):
            return

        # Check for UUID to detect echoes of our own messages
        msg_uuid: str | None = None
        if "uuid" in parsed and isinstance(parsed["uuid"], str):
            msg_uuid = parsed["uuid"]

        if msg_uuid and recent_posted_uuids.has(msg_uuid):
            _log_for_debugging(f"Ignoring echo: type={parsed.get('type')} uuid={msg_uuid}")
            return

        # Defensive dedup: drop inbound prompts we've already forwarded
        if msg_uuid and recent_inbound_uuids.has(msg_uuid):
            _log_for_debugging(
                f"Ignoring re-delivered inbound: type={parsed.get('type')} uuid={msg_uuid}"
            )
            return

        _log_for_debugging(
            f"Ingress message type={parsed.get('type')}"
            + (f" uuid={msg_uuid}" if msg_uuid else "")
        )

        if parsed.get("type") == "user":
            if msg_uuid:
                recent_inbound_uuids.add(msg_uuid)
            # Fire-and-forget — handler may be async
            if on_inbound_message:
                on_inbound_message(parsed)
        else:
            _log_for_debugging(
                f"Ignoring non-user inbound message: type={parsed.get('type')}"
            )

    except Exception as err:
        _log_for_debugging(f"Failed to parse ingress message: {err}")


# =============================================================================
# Server Control Request Handlers
# =============================================================================


@dataclass
class ServerControlRequestHandlers:
    """Handlers for server-initiated control requests."""

    transport: BridgeTransport | None = None
    session_id: str = ""
    outbound_only: bool = False
    on_interrupt: Callable[[], None] | None = None
    on_set_model: Callable[[str | None], None] | None = None
    on_set_max_thinking_tokens: Callable[[int | None], None] | None = None
    on_set_permission_mode: Callable[
        [str], dict[str, Any]
    ] | None = None  # Returns {ok: bool, error?: str}


OUTBOUND_ONLY_ERROR = (
    "This session is outbound-only. "
    "Enable Remote Control locally to allow inbound control."
)


def handle_server_control_request(
    request: SDKControlRequest,
    handlers: ServerControlRequestHandlers,
) -> None:
    """Respond to inbound control_request messages from the server.

    The server sends these for session lifecycle events (initialize, set_model)
    and for turn-level coordination (interrupt, set_max_thinking_tokens). If we
    don't respond, the server hangs and kills the WS after ~10-14s.

    Args:
        request: The control request from the server.
        handlers: Object containing transport and callback handlers.
    """
    transport = handlers.transport
    if not transport:
        _log_for_debugging(
            "Cannot respond to control_request: transport not configured"
        )
        return

    request_subtype = request.get("request", {}).get("subtype", "")

    # Outbound-only: reply error for mutable requests
    if handlers.outbound_only and request_subtype != "initialize":
        response = _make_control_response(
            session_id=handlers.session_id,
            request_id=request.get("request_id", ""),
            subtype="error",
            error=OUTBOUND_ONLY_ERROR,
        )
        transport.write(response)
        _log_for_debugging(
            f"Rejected {request_subtype} (outbound-only) "
            f"request_id={request.get('request_id')}"
        )
        return

    # Handle each request type
    if request_subtype == "initialize":
        response = _handle_initialize(handlers)
    elif request_subtype == "set_model":
        model = request.get("request", {}).get("model")
        if handlers.on_set_model:
            handlers.on_set_model(model)
        response = _make_control_response(
            session_id=handlers.session_id,
            request_id=request.get("request_id", ""),
            subtype="success",
        )
    elif request_subtype == "set_max_thinking_tokens":
        max_tokens = request.get("request", {}).get("max_thinking_tokens")
        if handlers.on_set_max_thinking_tokens:
            handlers.on_set_max_thinking_tokens(max_tokens)
        response = _make_control_response(
            session_id=handlers.session_id,
            request_id=request.get("request_id", ""),
            subtype="success",
        )
    elif request_subtype == "set_permission_mode":
        mode = request.get("request", {}).get("mode", "auto")
        if handlers.on_set_permission_mode:
            verdict = handlers.on_set_permission_mode(mode)
        else:
            verdict = {
                "ok": False,
                "error": "set_permission_mode is not supported in this context "
                "(onSetPermissionMode callback not registered)",
            }

        if verdict.get("ok"):
            response = _make_control_response(
                session_id=handlers.session_id,
                request_id=request.get("request_id", ""),
                subtype="success",
            )
        else:
            response = _make_control_response(
                session_id=handlers.session_id,
                request_id=request.get("request_id", ""),
                subtype="error",
                error=verdict.get("error", "Unknown error"),
            )
    elif request_subtype == "interrupt":
        if handlers.on_interrupt:
            handlers.on_interrupt()
        response = _make_control_response(
            session_id=handlers.session_id,
            request_id=request.get("request_id", ""),
            subtype="success",
        )
    else:
        # Unknown subtype — respond with error
        response = _make_control_response(
            session_id=handlers.session_id,
            request_id=request.get("request_id", ""),
            subtype="error",
            error=f"REPL bridge does not handle control_request subtype: {request_subtype}",
        )

    transport.write(response)
    _log_for_debugging(
        f"Sent control_response for {request_subtype} "
        f"request_id={request.get('request_id')} "
        f"result={response.get('response', {}).get('subtype')}"
    )


def _handle_initialize(handlers: ServerControlRequestHandlers) -> SDKControlResponse:
    """Handle initialize control request.

    Respond with minimal capabilities — the REPL handles
    commands, models, and account info itself.
    """
    import os

    pid = os.getpid()
    return _make_control_response(
        session_id=handlers.session_id,
        request_id="",  # Initialize may not have request_id
        subtype="success",
        response_data={
            "commands": [],
            "output_style": "normal",
            "available_output_styles": ["normal"],
            "models": [],
            "account": {},
            "pid": pid,
        },
    )


def _make_control_response(
    session_id: str,
    request_id: str,
    subtype: str,
    error: str | None = None,
    response_data: dict[str, Any] | None = None,
) -> SDKControlResponse:
    """Build a control_response message."""
    response: SDKControlResponse = {
        "type": "control_response",
        "session_id": session_id,
        "response": {
            "subtype": subtype,
            "request_id": request_id,
        },
    }
    if error:
        response["response"]["error"] = error
    if response_data:
        response["response"]["response"] = response_data
    return response


# =============================================================================
# Result Message (for session archival on teardown)
# =============================================================================


def make_result_message(session_id: str) -> dict[str, Any]:
    """Build a minimal SDKResultSuccess message for session archival.

    The server needs this event before a WS close to trigger archival.

    Args:
        session_id: The session ID for the result message.

    Returns:
        A result success message dict.
    """
    return {
        "type": "result",
        "subtype": "success",
        "duration_ms": 0,
        "duration_api_ms": 0,
        "is_error": False,
        "num_turns": 0,
        "result": "",
        "stop_reason": None,
        "total_cost_usd": 0.0,
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "model_usage": {},
        "permission_denials": [],
        "session_id": session_id,
        "uuid": str(uuid.uuid4()),
    }


# =============================================================================
# BoundedUUIDSet (echo-dedup ring buffer)
# =============================================================================


class BoundedUUIDSet:
    """FIFO-bounded set backed by a circular buffer.

    Evicts the oldest entry when capacity is reached, keeping memory
    usage constant at O(capacity).

    Messages are added in chronological order, so evicted entries are
    always the oldest. The caller relies on external ordering as the
    primary dedup — this set is a secondary safety net for echo filtering
    and race-condition dedup.
    """

    def __init__(self, capacity: int = 100) -> None:
        """Initialize the bounded set.

        Args:
            capacity: Maximum number of UUIDs to store.
        """
        self._capacity = capacity
        self._ring: list[str | None] = [None] * capacity
        self._set: set[str] = set()
        self._write_idx = 0

    def add(self, uuid_str: str) -> None:
        """Add a UUID to the set.

        Args:
            uuid_str: The UUID to add.
        """
        if uuid_str in self._set:
            return

        # Evict the entry at the current write position
        evicted = self._ring[self._write_idx]
        if evicted is not None:
            self._set.discard(evicted)

        self._ring[self._write_idx] = uuid_str
        self._set.add(uuid_str)
        self._write_idx = (self._write_idx + 1) % self._capacity

    def has(self, uuid_str: str) -> bool:
        """Check if a UUID is in the set.

        Args:
            uuid_str: The UUID to check.

        Returns:
            True if the UUID is present.
        """
        return uuid_str in self._set

    def clear(self) -> None:
        """Clear all entries from the set."""
        self._set.clear()
        for i in range(self._capacity):
            self._ring[i] = None
        self._write_idx = 0


# =============================================================================
# Bridge Transport Protocol
# =============================================================================


class BridgeTransport(Protocol):
    """Protocol for bridge transport implementations."""

    def write(self, message: dict[str, Any]) -> None:
        """Write a message to the transport."""
        ...

    def close(self) -> None:
        """Close the transport."""
        ...
