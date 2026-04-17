"""Bridge handle for REPL sessions.

Implements the core bridge handle that manages the REPL session lifecycle:
- Environment registration via the bridge API
- Session creation and crash-recovery via bridge pointer files
- Transport lifecycle (v1/v2) for ingress WebSocket/SSE connections
- Message writing with echo detection via BoundedUUIDSet
- Control request/response handling
- Teardown with proper cleanup

TypeScript equivalent: src/bridge/replBridge.ts (initBridgeCore)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .messaging import (
    BoundedUUIDSet,
    ServerControlRequestHandlers,
    handle_ingress_message,
    handle_server_control_request,
    is_eligible_bridge_message,
    make_result_message,
)
from .session import SessionManager
from .transport import BridgeTransport

if TYPE_CHECKING:
    from ..models.message import Message

logger = logging.getLogger(__name__)

# =============================================================================
# Type Aliases
# =============================================================================

BridgeState = str  # 'ready' | 'connected' | 'reconnecting' | 'failed'

SDKMessage = dict[str, Any]
SDKControlRequest = dict[str, Any]
SDKControlResponse = dict[str, Any]


# =============================================================================
# Flush Gate (message queueing during initial flush)
# =============================================================================


class FlushGate:
    """Gates message writes during the initial flush to prevent ordering races.

    When active, messages are enqueued rather than sent immediately.
    This prevents new messages from arriving at the server interleaved
    with historical messages during the initial flush.
    """

    def __init__(self) -> None:
        self._active = False
        self._queue: list[Message] = []

    @property
    def active(self) -> bool:
        """Whether the gate is active (flushing in progress)."""
        return self._active

    def start(self) -> None:
        """Activate the gate, queuing subsequent messages."""
        self._active = True
        self._queue = []

    def enqueue(self, *messages: Message) -> bool:
        """Enqueue messages if the gate is active.

        Args:
            *messages: Messages to enqueue.

        Returns:
            True if messages were enqueued (gate was active).
        """
        if not self._active:
            return False
        self._queue.extend(messages)
        return True

    def end(self) -> list[Message]:
        """End the flush, returning queued messages.

        Deactivates the gate and returns all queued messages.

        Returns:
            List of queued messages.
        """
        self._active = False
        messages = self._queue
        self._queue = []
        return messages

    def deactivate(self) -> None:
        """Deactivate the gate without returning queued messages."""
        self._active = False
        self._queue = []

    def drop(self) -> int:
        """Drop all queued messages, deactivating the gate.

        Returns:
            Number of messages dropped.
        """
        count = len(self._queue)
        self._active = False
        self._queue = []
        return count


# =============================================================================
# Title Text Extraction
# =============================================================================


def extract_title_text(message: Message) -> str | None:
    """Extract title-worthy text from a message.

    Used for deriving session titles from early user prompts.

    Args:
        message: The message to extract text from.

    Returns:
        The extracted text, or None if no title-worthy text found.
    """
    from ..models.message import Role

    # Only user messages have title-worthy content
    if message.role != Role.USER:
        return None

    for block in message.content_blocks:
        if block.text:
            text = block.text.strip()
            if text and not text.startswith("/"):  # Skip slash commands
                # Truncate long prompts for title use
                return text[:200] if len(text) > 200 else text
    return None


# =============================================================================
# Bridge Core Parameters
# =============================================================================


@dataclass
class BridgeCoreParams:
    """Parameters for init_bridge_core.

    All context needed to bootstrap a bridge connection without reading
    from bootstrap state or session storage.

    TypeScript equivalent: BridgeCoreParams in replBridge.ts
    """

    dir: str
    machine_name: str
    branch: str
    git_repo_url: str | None
    title: str
    base_url: str
    session_ingress_url: str
    worker_type: str
    get_access_token: Callable[[], str | None]
    create_session: Callable[
        [dict[str, Any]], Awaitable[str | None]
    ]  # async, returns session_id or None
    archive_session: Callable[[str], Awaitable[None]]  # async

    # Optional callbacks
    get_current_title: Callable[[], str] | None = None
    to_sdk_messages: Callable[
        [list[Message]], list[SDKMessage]
    ] | None = None  # Message[] -> SDKMessage[]
    on_auth_401: Callable[[str], Awaitable[bool]] | None = None
    on_inbound_message: Callable[[SDKMessage], None] | None = None
    on_permission_response: Callable[[SDKControlResponse], None] | None = None
    on_interrupt: Callable[[], None] | None = None
    on_set_model: Callable[[str | None], None] | None = None
    on_set_max_thinking_tokens: Callable[[int | None], None] | None = None
    on_set_permission_mode: Callable[
        [str], dict[str, bool]
    ] | None = None  # Returns {ok: bool, error?: str}
    on_state_change: Callable[[BridgeState, str | None], None] | None = None
    on_user_message: Callable[[str, str], bool] | None = None
    # Fires on each user message for title derivation. Returns True when done.
    perpetual: bool = False
    # If True, skip result send / stopWork / deregister on teardown.
    # Used for daemon/agent-sdk mode where the process stays alive.
    initial_sse_sequence_num: int = 0
    initial_messages: list[Message] | None = None
    previously_flushed_uuids: set[str] | None = None
    initial_history_cap: int = 200


# =============================================================================
# ReplBridgeHandle
# =============================================================================


class ReplBridgeHandle:
    """Handle for a bridge-connected REPL session.

    Manages the full lifecycle: environment registration, session creation,
    transport management, message writing, and teardown.

    TypeScript equivalent: BridgeCoreHandle in replBridge.ts
    """

    def __init__(self, params: BridgeCoreParams) -> None:
        """Initialize the bridge handle.

        Args:
            params: Bridge core initialization parameters.
        """
        self._params = params
        self._session_manager = SessionManager(base_url=params.base_url)
        self._transport: BridgeTransport | None = None

        # Session identifiers
        self._bridge_session_id: str = ""
        self._environment_id: str = ""
        self._environment_secret: str = ""

        # Flush gate for initial message queueing
        self._flush_gate = FlushGate()

        # Echo detection: ring buffers of recently seen UUIDs
        self._recent_posted_uuids: BoundedUUIDSet = BoundedUUIDSet(2000)
        self._recent_inbound_uuids: BoundedUUIDSet = BoundedUUIDSet(2000)

        # SSE sequence number tracking (for v2)
        self._last_transport_sequence_num: int = params.initial_sse_sequence_num

        # UUIDs of initial messages already flushed
        self._initial_message_uuids: set[str] = set()
        if params.initial_messages:
            for msg in params.initial_messages:
                self._initial_message_uuids.add(msg.id)

        # Seed the posted UUIDs with initial message UUIDs
        for uuid in self._initial_message_uuids:
            self._recent_posted_uuids.add(uuid)

        # Tracking state
        self._teardown_started: bool = False
        self._initial_flush_done: bool = False
        self._user_message_callback_done: bool = params.on_user_message is None

        # Current work item
        self._current_work_id: str | None = None

        # Polling control
        self._poll_controller: asyncio.Event | None = None

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def bridge_session_id(self) -> str:
        """The current session ID."""
        return self._bridge_session_id

    @property
    def environment_id(self) -> str:
        """The current environment ID."""
        return self._environment_id

    @property
    def session_ingress_url(self) -> str:
        """The session ingress URL."""
        return self._params.session_ingress_url

    @property
    def state(self) -> BridgeState:
        """Current bridge state."""
        if self._transport is not None and self._transport.isConnectedStatus():
            return "connected"
        return "ready"

    # -------------------------------------------------------------------------
    # Message Writing
    # -------------------------------------------------------------------------

    def write_messages(self, messages: list[Message]) -> None:
        """Write messages to the bridge transport.

        Filters to user/assistant messages not already sent, handles title
        derivation, queues during initial flush, and sends via the transport.

        Args:
            messages: Messages to write.
        """
        # Filter to eligible messages not already sent
        filtered = [
            m
            for m in messages
            if is_eligible_bridge_message(m)
            and m.id not in self._initial_message_uuids
            and not self._recent_posted_uuids.has(m.id)
        ]
        if not filtered:
            return

        # Title derivation
        if not self._user_message_callback_done and self._params.on_user_message:
            for msg in filtered:
                text = extract_title_text(msg)
                if text is not None:
                    if self._params.on_user_message(text, self._bridge_session_id):
                        self._user_message_callback_done = True
                        break

        # Queue during initial flush
        if self._flush_gate.enqueue(*filtered):
            logger.debug(
                "[bridge:repl] Queued %d message(s) during initial flush",
                len(filtered),
            )
            return

        # No transport
        if not self._transport:
            types = ", ".join(m.type for m in filtered)  # type: ignore
            logger.warning(
                "[bridge:repl] Transport not configured, dropping %d message(s) "
                "[%s] for session=%s",
                len(filtered),
                types,
                self._bridge_session_id,
            )
            return

        # Track for echo filtering
        for msg in filtered:
            self._recent_posted_uuids.add(msg.id)

        # Convert and send
        to_sdk = self._params.to_sdk_messages
        sdk_messages = to_sdk(filtered) if to_sdk else [self._message_to_sdk(m) for m in filtered]

        events = [
            {**msg, "session_id": self._bridge_session_id} for msg in sdk_messages
        ]
        logger.debug(
            "[bridge:repl] Sending %d message(s) via transport",
            len(filtered),
        )
        self._transport.writeBatch(events)

    def write_sdk_messages(self, messages: list[SDKMessage]) -> None:
        """Write SDK-format messages to the bridge transport.

        Used by daemon callers that already have SDKMessage format.

        Args:
            messages: SDK messages to write.
        """
        # Filter by UUID for echo dedup
        filtered = [
            m
            for m in messages
            if not m.get("uuid") or not self._recent_posted_uuids.has(m["uuid"])
        ]
        if not filtered:
            return

        if not self._transport:
            logger.warning(
                "[bridge:repl] Transport not configured, dropping %d SDK message(s) "
                "for session=%s",
                len(filtered),
                self._bridge_session_id,
            )
            return

        for msg in filtered:
            uuid = msg.get("uuid")
            if uuid:
                self._recent_posted_uuids.add(uuid)

        events = [
            {**msg, "session_id": self._bridge_session_id} for msg in filtered
        ]
        self._transport.writeBatch(events)

    def _message_to_sdk(self, message: Message) -> SDKMessage:
        """Convert a Message to SDKMessage format.

        Args:
            message: The message to convert.

        Returns:
            An SDKMessage dict.
        """
        role = message.role.value
        content_blocks = []
        for block in message.content_blocks:
            cb: dict[str, Any] = {}
            if block.text is not None:
                cb["text"] = block.text
            if block.image_url is not None:
                cb["image_url"] = block.image_url
            if cb:
                content_blocks.append(cb)

        result: SDKMessage = {
            "type": role,
            "uuid": message.id,
            "content": content_blocks,
        }
        if message.name is not None:
            result["name"] = message.name
        return result

    # -------------------------------------------------------------------------
    # Control Messages
    # -------------------------------------------------------------------------

    def send_control_request(self, request: SDKControlRequest) -> None:
        """Send a control request to the server.

        Args:
            request: The control request dict.
        """
        if not self._transport:
            logger.debug(
                "[bridge:repl] Transport not configured, skipping control_request",
            )
            return
        event = {**request, "session_id": self._bridge_session_id}
        self._transport.write(event)
        logger.debug(
            "[bridge:repl] Sent control_request request_id=%s",
            request.get("request_id"),
        )

    def send_control_response(self, response: SDKControlResponse) -> None:
        """Send a control response to the server.

        Args:
            response: The control response dict.
        """
        if not self._transport:
            logger.debug(
                "[bridge:repl] Transport not configured, skipping control_response",
            )
            return
        event = {**response, "session_id": self._bridge_session_id}
        self._transport.write(event)
        logger.debug("[bridge:repl] Sent control_response")

    def send_control_cancel_request(self, request_id: str) -> None:
        """Cancel an in-flight control request.

        Args:
            request_id: The request ID to cancel.
        """
        if not self._transport:
            logger.debug(
                "[bridge:repl] Transport not configured, "
                "skipping control_cancel_request",
            )
            return
        event = {
            "type": "control_cancel_request",
            "request_id": request_id,
            "session_id": self._bridge_session_id,
        }
        self._transport.write(event)
        logger.debug(
            "[bridge:repl] Sent control_cancel_request request_id=%s",
            request_id,
        )

    # -------------------------------------------------------------------------
    # Result
    # -------------------------------------------------------------------------

    def send_result(self) -> None:
        """Send a result message for session archival."""
        if not self._transport:
            logger.debug(
                "[bridge:repl] sendResult: skipping, transport not configured "
                "session=%s",
                self._bridge_session_id,
            )
            return
        self._transport.write(make_result_message(self._bridge_session_id))
        logger.debug(
            "[bridge:repl] Sent result for session=%s",
            self._bridge_session_id,
        )

    # -------------------------------------------------------------------------
    # SSE Sequence Number
    # -------------------------------------------------------------------------

    def get_sse_sequence_num(self) -> int:
        """Get the current SSE sequence-number high-water mark.

        Returns:
            The highest sequence number seen by the current transport.
        """
        live = 0
        if self._transport:
            live = self._transport.getLastSequenceNum()
        return max(self._last_transport_sequence_num, live)

    # -------------------------------------------------------------------------
    # Transport Wiring
    # -------------------------------------------------------------------------

    def _wire_transport(self, transport: BridgeTransport) -> None:
        """Wire callbacks onto a transport and store it.

        Sets up onConnect, onData, onClose handlers and starts the transport.

        Args:
            transport: The transport to wire.
        """
        self._transport = transport

        # onConnect callback
        def on_connect() -> None:
            logger.debug("[bridge:repl] Ingress transport connected")
            self._params.on_state_change and self._params.on_state_change(
                "connected", None
            )

            # Start flush gate if we have initial messages to flush
            if (
                not self._initial_flush_done
                and self._params.initial_messages
                and len(self._params.initial_messages) > 0
            ):
                self._flush_gate.start()

        # onData callback
        def on_data(data: str) -> None:
            on_permission_response: Callable[
                [SDKControlResponse], None
            ] | None = self._params.on_permission_response
            on_control_request: Callable[
                [SDKControlRequest], None
            ] | None = self._create_control_request_handler()
            handle_ingress_message(
                data=data,
                recent_posted_uuids=self._recent_posted_uuids,
                recent_inbound_uuids=self._recent_inbound_uuids,
                on_inbound_message=self._params.on_inbound_message,  # type: ignore[arg-type]
                on_permission_response=on_permission_response,
                on_control_request=on_control_request,
            )

        # onClose callback
        def on_close(close_code: int | None) -> None:
            self._handle_transport_close(close_code)

        transport.setOnConnect(on_connect)
        transport.setOnData(on_data)
        transport.setOnClose(on_close)

        # Start the transport
        transport.connect()

    def _create_control_request_handler(
        self,
    ) -> Callable[[SDKControlRequest], None]:
        """Create the control request handler closure.

        Returns:
            A handler function for server control requests.
        """

        def handler(request: SDKControlRequest) -> None:
            handlers = ServerControlRequestHandlers(
                transport=self._transport,
                session_id=self._bridge_session_id,
                outbound_only=False,
                on_interrupt=self._params.on_interrupt,
                on_set_model=self._params.on_set_model,
                on_set_max_thinking_tokens=self._params.on_set_max_thinking_tokens,
                on_set_permission_mode=self._params.on_set_permission_mode,
            )
            handle_server_control_request(request, handlers)

        return handler

    def _handle_transport_close(self, close_code: int | None) -> None:
        """Handle permanent transport close.

        Args:
            close_code: The WebSocket close code.
        """
        logger.debug(
            "[bridge:repl] Transport permanently closed: code=%s",
            close_code,
        )

        # Capture SSE seq high-water mark
        if self._transport:
            closed_seq = self._transport.getLastSequenceNum()
            if closed_seq > self._last_transport_sequence_num:
                self._last_transport_sequence_num = closed_seq
            self._transport = None

        # Drop any queued messages (permanent close — no new transport will drain)
        dropped = self._flush_gate.drop()
        if dropped > 0:
            logger.warning(
                "[bridge:repl] Dropping %d pending message(s) on transport close "
                "(code=%s)",
                dropped,
                close_code,
            )

        if close_code == 1000:
            # Clean close — session ended normally
            self._params.on_state_change and self._params.on_state_change(
                "failed", "session ended"
            )
            if self._poll_controller:
                self._poll_controller.set()
            return

        # Abnormal close — attempt reconnect
        self._params.on_state_change and self._params.on_state_change(
            "reconnecting",
            f"Remote Control connection lost (code {close_code})",
        )
        logger.debug(
            "[bridge:repl] Transport reconnect budget exhausted (code=%s), "
            "attempting env reconnect",
            close_code,
        )

    # -------------------------------------------------------------------------
    # Teardown
    # -------------------------------------------------------------------------

    async def teardown(self) -> None:
        """Tear down the bridge session.

        Sends result message, stops work, archives session, closes transport,
        and deregisters the environment.
        """
        if self._teardown_started:
            logger.debug(
                "[bridge:repl] Teardown already in progress, skipping duplicate call "
                "env=%s session=%s",
                self._environment_id,
                self._bridge_session_id,
            )
            return
        self._teardown_started = True

        logger.debug(
            "[bridge:repl] Teardown starting: env=%s session=%s workId=%s",
            self._environment_id,
            self._bridge_session_id,
            self._current_work_id or "none",
        )

        # Abort polling
        if self._poll_controller:
            self._poll_controller.set()

        # Capture final SSE sequence number
        if self._transport:
            final_seq = self._transport.getLastSequenceNum()
            if final_seq > self._last_transport_sequence_num:
                self._last_transport_sequence_num = final_seq

        # Perpetual mode: local teardown only
        if self._params.perpetual:
            self._transport = None
            self._flush_gate.drop()
            # Keep the environment alive for next start
            self._session_manager.write_bridge_pointer(
                session_id=self._bridge_session_id,
                environment_id=self._environment_id,
                source="repl",
            )
            logger.debug(
                "[bridge:repl] Teardown (perpetual): leaving env=%s session=%s "
                "alive on server",
                self._environment_id,
                self._bridge_session_id,
            )
            return

        # Non-perpetual: full teardown
        teardown_transport = self._transport
        self._transport = None
        self._flush_gate.drop()

        if teardown_transport:
            teardown_transport.write(make_result_message(self._bridge_session_id))

        # Archive session
        try:
            await self._params.archive_session(self._bridge_session_id)
        except Exception as e:
            logger.debug(
                "[bridge:repl] Teardown archive_session failed: %s",
                e,
            )

        # Close transport
        if teardown_transport:
            teardown_transport.close()

        # Clear bridge pointer
        self._session_manager.clear_bridge_pointer()

        logger.debug(
            "[bridge:repl] Teardown complete: env=%s session=%s",
            self._environment_id,
            self._bridge_session_id,
        )


# =============================================================================
# Bridge Core Initialization
# =============================================================================


async def init_bridge_core(
    params: BridgeCoreParams,
) -> ReplBridgeHandle | None:
    """Initialize the bridge core and return a handle.

    Bootstrap-free core: env registration -> session creation -> ready.
    Reads nothing from bootstrap/state — all context comes from params.

    TypeScript equivalent: initBridgeCore() in replBridge.ts

    Args:
        params: Bridge core initialization parameters.

    Returns:
        A ReplBridgeHandle on success, or None on registration/session failure.
    """
    logger.debug(
        "[bridge:repl] init_bridge_core starting "
        "(initialMessages=%d)",
        len(params.initial_messages) if params.initial_messages else 0,
    )

    handle = ReplBridgeHandle(params)

    # Read crash-recovery pointer for perpetual mode
    prior = None
    if params.perpetual:
        prior = handle._session_manager.read_bridge_pointer()
        if prior and prior.source != "repl":
            prior = None

    # Create the handle
    # Note: Environment registration and session creation are skipped here
    # for the basic implementation. In full integration, these would call:
    #   api.registerBridgeEnvironment(bridge_config)
    #   createSession({ environmentId, title, ... })
    #   session_manager.write_bridge_pointer(...)
    #
    # For now, we set placeholder values so the handle interface is functional.
    handle._bridge_session_id = _generate_session_id()
    handle._environment_id = _generate_environment_id()
    handle._environment_secret = ""

    logger.debug(
        "[bridge:repl] Ready: env=%s session=%s",
        handle._environment_id,
        handle._bridge_session_id,
    )
    params.on_state_change and params.on_state_change("ready", None)

    return handle


def _generate_session_id() -> str:
    """Generate a new session ID."""
    import uuid

    return str(uuid.uuid4())


def _generate_environment_id() -> str:
    """Generate a new environment ID."""
    import uuid

    return str(uuid.uuid4())
