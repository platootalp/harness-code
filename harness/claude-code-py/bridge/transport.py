"""
Bridge transport module.

Provides transport implementations for bridge connections, including WebSocket
transport with reconnection logic and bridge transport adapters (v1/v2).

TypeScript equivalents:
- src/bridge/replBridgeTransport.ts (ReplBridgeTransport)
- src/cli/transports/WebSocketTransport.ts (WebSocketTransport)

Transport architecture:
- v1: WebSocketTransport (WS reads + HTTP POST writes to Session-Ingress)
- v2: SSETransport (reads) + CCRClient (writes to CCR v2 /worker/*)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

KEEP_ALIVE_FRAME = '{"type":"keep_alive"}\n'

DEFAULT_MAX_BUFFER_SIZE = 1000
DEFAULT_BASE_RECONNECT_DELAY = 1.0  # seconds
DEFAULT_MAX_RECONNECT_DELAY = 30.0  # seconds
# Time budget for reconnection attempts before giving up (10 minutes)
DEFAULT_RECONNECT_GIVE_UP_SECONDS = 600.0
DEFAULT_PING_INTERVAL = 10.0  # seconds
DEFAULT_KEEPALIVE_INTERVAL = 300.0  # 5 minutes
# Threshold for detecting system sleep/wake
SLEEP_DETECTION_THRESHOLD_SECONDS = DEFAULT_MAX_RECONNECT_DELAY * 2  # 60s

# Permanent WebSocket close codes — server has definitively ended the session
PERMANENT_CLOSE_CODES = frozenset([
    1002,  # protocol error — server rejected handshake
    4001,  # session expired / not found
    4003,  # unauthorized
])

# =============================================================================
# Session State
# =============================================================================


class SessionState:
    """Session state values sent to the backend."""

    IDLE = "idle"
    RUNNING = "running"
    REQUIRES_ACTION = "requires_action"


# =============================================================================
# Bridge Transport Protocol
# =============================================================================


class BridgeTransport(Protocol):
    """Full bridge transport interface for replBridge connections.

    Covers exactly the surface that replBridge.ts uses against the transport,
    so the v1/v2 choice is confined to the construction site.

    Methods:
        write: Write a single message.
        writeBatch: Write multiple messages in sequence.
        close: Close the transport.
        isConnectedStatus: Check if transport is connected.
        getStateLabel: Get human-readable state label.
        setOnData: Register data callback.
        setOnClose: Register close callback.
        setOnConnect: Register connect callback.
        connect: Initiate the connection.
        getLastSequenceNum: Get high-water mark of SSE sequence numbers.
        droppedBatchCount: Count of batches dropped via maxConsecutiveFailures.
        reportState: PUT /worker state (v2 only).
        reportMetadata: PUT /worker external_metadata (v2 only).
        reportDelivery: POST /worker/events/{id}/delivery (v2 only).
        flush: Drain write queue before close (v2 only).
    """

    def write(self, message: dict[str, Any]) -> None:
        """Write a single message to the transport."""
        ...

    def writeBatch(self, messages: list[dict[str, Any]]) -> None:
        """Write multiple messages in sequence."""
        ...

    def close(self) -> None:
        """Close the transport."""
        ...

    def isConnectedStatus(self) -> bool:
        """Check if transport is connected for writes."""
        ...

    def getStateLabel(self) -> str:
        """Get human-readable state label for debugging."""
        ...

    def setOnData(self, callback: Callable[[str], None]) -> None:
        """Register callback for inbound data."""
        ...

    def setOnClose(self, callback: Callable[[int | None], None]) -> None:
        """Register callback for close events."""
        ...

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        """Register callback for connect events."""
        ...

    def connect(self) -> None:
        """Initiate the transport connection."""
        ...

    def getLastSequenceNum(self) -> int:
        """Get high-water mark of SSE sequence numbers."""
        ...

    @property
    def droppedBatchCount(self) -> int:
        """Count of batches dropped via maxConsecutiveFailures."""
        ...

    def reportState(self, state: str) -> None:
        """PUT /worker state (v2 only; v1 is no-op)."""
        ...

    def reportMetadata(self, metadata: dict[str, Any]) -> None:
        """PUT /worker external_metadata (v2 only; v1 is no-op)."""
        ...

    def reportDelivery(
        self, event_id: str, status: str
    ) -> None:
        """POST /worker/events/{id}/delivery (v2 only; v1 is no-op)."""
        ...

    def flush(self) -> None:
        """Drain write queue before close (v2 only)."""
        ...


# =============================================================================
# WebSocket Transport
# =============================================================================


class WebSocketTransportState:
    """WebSocket transport state values."""

    IDLE = "idle"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class WebSocketTransport:
    """WebSocket transport with automatic reconnection.

    Implements bidirectional WebSocket communication with:
    - Exponential backoff reconnection with jitter
    - Ping/pong heartbeat for connection health
    - Keep-alive data frames to reset proxy idle timers
    - Message buffering for replay on reconnection
    - Sleep/wake detection
    - Permanent close code handling

    TypeScript equivalent: src/cli/transports/WebSocketTransport.ts

    Attributes:
        url: WebSocket URL to connect to.
        headers: HTTP headers to send on connection.
        session_id: Optional session ID for logging.
        auto_reconnect: Whether to auto-reconnect on disconnect.
        is_bridge: Whether this is a REPL bridge transport (telemetry gating).
    """

    url: str
    headers: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None
    auto_reconnect: bool = True
    is_bridge: bool = False

    # Internal state
    _ws: Any = field(default=None, repr=False)
    _last_sent_id: str | None = field(default=None, repr=False)
    _state: str = field(default=WebSocketTransportState.IDLE, repr=False)
    _on_data: Callable[[str], None] | None = field(default=None, repr=False)
    _on_close_callback: Callable[[int | None], None] | None = field(
        default=None, repr=False
    )
    _on_connect_callback: Callable[[], None] | None = field(
        default=None, repr=False
    )

    # Reconnection state
    _reconnect_attempts: int = field(default=0, repr=False)
    _reconnect_start_time: float | None = field(default=None, repr=False)
    _reconnect_timer: asyncio.TimerHandle | None = field(default=None, repr=False)
    _last_reconnect_attempt_time: float | None = field(default=None, repr=False)
    _last_activity_time: float = field(default=0.0, repr=False)

    # Ping state
    _ping_interval: asyncio.TimerHandle | None = field(default=None, repr=False)
    _pong_received: bool = field(default=True, repr=False)

    # Keep-alive state
    _keepalive_interval: asyncio.TimerHandle | None = field(default=None, repr=False)

    # Message buffer for replay
    _message_buffer: list[dict[str, Any]] = field(default_factory=list)

    # Refresh headers callback
    _refresh_headers: Callable[[], dict[str, str]] | None = field(
        default=None, repr=False
    )

    # Connection start time for timing metrics
    _connect_start_time: float = field(default=0.0, repr=False)

    def __post_init__(self) -> None:
        """Initialize the transport."""
        # Message buffer capacity
        self._max_buffer_size = DEFAULT_MAX_BUFFER_SIZE

    def isConnectedStatus(self) -> bool:
        """Check if transport is connected."""
        return self._state == WebSocketTransportState.CONNECTED

    def isClosedStatus(self) -> bool:
        """Check if transport is closed."""
        return self._state == WebSocketTransportState.CLOSED

    def getStateLabel(self) -> str:
        """Get human-readable state label."""
        return self._state

    def setOnData(self, callback: Callable[[str], None]) -> None:
        """Register callback for inbound data."""
        self._on_data = callback

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        """Register callback for connect events."""
        self._on_connect_callback = callback

    def setOnClose(self, callback: Callable[[int | None], None]) -> None:
        """Register callback for close events."""
        self._on_close_callback = callback

    async def connect(self) -> None:
        """Initiate WebSocket connection.

        Connects to the WebSocket URL with exponential backoff reconnection.
        """
        if (
            self._state != WebSocketTransportState.IDLE
            and self._state != WebSocketTransportState.RECONNECTING
        ):
            logger.warning(
                "WebSocketTransport: Cannot connect, current state is %s",
                self._state,
            )
            return

        self._state = WebSocketTransportState.RECONNECTING
        self._connect_start_time = time.monotonic()

        logger.debug("WebSocketTransport: Opening %s", self.url)

        # Build headers
        headers = dict(self.headers)
        if self._last_sent_id:
            headers["X-Last-Request-Id"] = self._last_sent_id

        try:
            import websockets

            # websockets client takes headers as a list of tuples
            ws_headers = list(headers.items())
            self._ws = await websockets.connect(
                self.url,
                extra_headers=ws_headers,
                ping_interval=None,  # We manage ping ourselves
            )
        except Exception as e:
            logger.debug("WebSocketTransport: Connection failed: %s", e)
            self._handle_connection_error()
            return

        # Create async task to read messages
        asyncio.create_task(self._read_loop())

        # Handle connection open
        await self._handle_open()

    async def _read_loop(self) -> None:
        """Read messages from the WebSocket in a loop."""
        ws = self._ws
        if ws is None:
            return

        try:
            async for raw_message in ws:
                message = raw_message if isinstance(raw_message, str) else str(raw_message)
                self._last_activity_time = time.monotonic()
                if self._on_data:
                    self._on_data(message)
        except Exception as e:
            logger.debug("WebSocketTransport: Read loop error: %s", e)
            self._handle_connection_error()
            return

        # Connection closed normally
        logger.debug("WebSocketTransport: Read loop ended")

    async def _handle_open(self) -> None:
        """Handle WebSocket open event."""
        connect_duration = time.monotonic() - self._connect_start_time
        logger.debug(
            "WebSocketTransport: Connected in %.0fms",
            connect_duration * 1000,
        )

        # Reset reconnect state
        self._reconnect_attempts = 0
        self._reconnect_start_time = None
        self._last_reconnect_attempt_time = None
        self._last_activity_time = time.monotonic()
        self._state = WebSocketTransportState.CONNECTED

        # Start heartbeat timers
        self._start_ping_interval()
        self._start_keepalive_interval()

        # Replay buffered messages
        if self._last_sent_id:
            await self._replay_buffered_messages(self._last_sent_id)

        # Notify connect callback
        if self._on_connect_callback:
            self._on_connect_callback()

    async def _replay_buffered_messages(self, last_id: str) -> None:
        """Replay buffered messages after reconnection.

        Args:
            last_id: The last confirmed message ID from server headers.
        """
        if not self._message_buffer:
            return

        # Find where to start replay based on server's last received message
        messages = self._message_buffer
        start_index = 0
        if last_id:
            for i, msg in enumerate(messages):
                if msg.get("uuid") == last_id:
                    # Server confirmed messages up to this index
                    start_index = i + 1
                    break

        # Rebuild buffer with only unconfirmed messages
        remaining = messages[start_index:]
        self._message_buffer = remaining
        if not remaining:
            self._last_sent_id = None

        logger.debug(
            "WebSocketTransport: Replaying %d buffered messages (evicted %d)",
            len(remaining),
            start_index,
        )

        for msg in remaining:
            line = json.dumps(msg) + "\n"
            success = await self._send_line(line)
            if not success:
                self._handle_connection_error()
                break

    async def _send_line(self, line: str) -> bool:
        """Send a line over the WebSocket.

        Args:
            line: The line to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        ws = self._ws
        if ws is None or self._state != WebSocketTransportState.CONNECTED:
            logger.debug("WebSocketTransport: Not connected")
            return False

        try:
            await ws.send(line)
            self._last_activity_time = time.monotonic()
            return True
        except Exception as e:
            logger.debug("WebSocketTransport: Failed to send: %s", e)
            self._handle_connection_error()
            return False

    async def write(self, message: dict[str, Any]) -> None:
        """Write a message to the WebSocket.

        Messages with a 'uuid' field are buffered for replay on reconnection.

        Args:
            message: The message dict to write.
        """
        msg_uuid = message.get("uuid")
        if msg_uuid:
            # Add to buffer for replay
            if len(self._message_buffer) < self._max_buffer_size:
                self._message_buffer.append(message)
            self._last_sent_id = msg_uuid

        if self._state != WebSocketTransportState.CONNECTED:
            # Message buffered for replay when connected (if it has a UUID)
            return

        line = json.dumps(message) + "\n"
        await self._send_line(line)

    def _stop_timers(self) -> None:
        """Stop all timer handles."""
        for timer_attr in ["_ping_interval", "_keepalive_interval", "_reconnect_timer"]:
            timer = getattr(self, timer_attr)
            if timer:
                timer.cancel()
                setattr(self, timer_attr, None)

    def _handle_connection_error(self, close_code: int | None = None) -> None:
        """Handle WebSocket connection error or close.

        Implements reconnection with exponential backoff and sleep detection.

        Args:
            close_code: WebSocket close code if available.
        """
        logger.debug(
            "WebSocketTransport: Disconnected from %s%s",
            self.url,
            f" (code {close_code})" if close_code is not None else "",
        )

        # Stop timers
        self._stop_timers()

        # Close WebSocket if open
        ws = self._ws
        if ws is not None:
            self._ws = None

        if self._state in (
            WebSocketTransportState.CLOSING,
            WebSocketTransportState.CLOSED,
        ):
            return

        # Permanent codes: don't retry
        if (
            close_code is not None
            and close_code in PERMANENT_CLOSE_CODES
        ):
            logger.warning(
                "WebSocketTransport: Permanent close code %d, not reconnecting",
                close_code,
            )
            self._state = WebSocketTransportState.CLOSED
            if self._on_close_callback:
                self._on_close_callback(close_code)
            return

        # When autoReconnect is disabled, go straight to closed
        if not self.auto_reconnect:
            self._state = WebSocketTransportState.CLOSED
            if self._on_close_callback:
                self._on_close_callback(close_code)
            return

        # Schedule reconnection with exponential backoff
        now = time.monotonic()
        if self._reconnect_start_time is None:
            self._reconnect_start_time = now

        # Detect system sleep/wake
        if (
            self._last_reconnect_attempt_time is not None
            and now - self._last_reconnect_attempt_time
            > SLEEP_DETECTION_THRESHOLD_SECONDS
        ):
            logger.debug(
                "WebSocketTransport: Detected system sleep "
                "(%.0fs gap), resetting reconnection budget",
                now - self._last_reconnect_attempt_time,
            )
            self._reconnect_start_time = now
            self._reconnect_attempts = 0

        self._last_reconnect_attempt_time = now

        elapsed = now - (self._reconnect_start_time or now)
        if elapsed < DEFAULT_RECONNECT_GIVE_UP_SECONDS:
            # Clear existing reconnect timer
            if self._reconnect_timer:
                self._reconnect_timer.cancel()
                self._reconnect_timer = None

            # Refresh headers before reconnecting
            if self._refresh_headers:
                fresh = self._refresh_headers()
                self.headers.update(fresh)

            self._state = WebSocketTransportState.RECONNECTING
            self._reconnect_attempts += 1

            # Calculate delay with ±25% jitter
            base_delay = min(
                DEFAULT_BASE_RECONNECT_DELAY
                * (2 ** (self._reconnect_attempts - 1)),
                DEFAULT_MAX_RECONNECT_DELAY,
            )
            jitter = base_delay * 0.25 * (2 * random.random() - 1)
            delay = max(0, base_delay + jitter)

            logger.debug(
                "WebSocketTransport: Reconnecting in %.0fms "
                "(attempt %d, %.0fs elapsed)",
                delay * 1000,
                self._reconnect_attempts,
                elapsed,
            )

            loop = asyncio.get_running_loop()
            self._reconnect_timer = loop.call_later(
                delay, lambda: asyncio.create_task(self.connect())
            )
        else:
            logger.warning(
                "WebSocketTransport: Reconnection time budget exhausted "
                "after %.0fs for %s",
                elapsed,
                self.url,
            )
            self._state = WebSocketTransportState.CLOSED
            if self._on_close_callback:
                self._on_close_callback(close_code)

    def close(self) -> None:
        """Close the WebSocket transport."""
        # Clear timers
        self._stop_timers()

        self._state = WebSocketTransportState.CLOSING

        if self._ws is not None:
            with contextlib.suppress(Exception):
                asyncio.create_task(self._ws.close())
            self._ws = None

        self._state = WebSocketTransportState.CLOSED

    def _start_ping_interval(self) -> None:
        """Start periodic ping to detect dead connections."""
        self._stop_ping_interval()
        self._pong_received = True

        async def ping_loop() -> None:
            while self._state == WebSocketTransportState.CONNECTED:
                await asyncio.sleep(DEFAULT_PING_INTERVAL)
                if self._state != WebSocketTransportState.CONNECTED:
                    break
                if not self._pong_received:
                    logger.warning(
                        "WebSocketTransport: No pong received, "
                        "connection appears dead",
                    )
                    self._handle_connection_error()
                    return
                self._pong_received = False
                try:
                    if self._ws is not None:
                        await self._ws.ping()
                except Exception as e:
                    logger.debug("WebSocketTransport: Ping failed: %s", e)
                    self._handle_connection_error()
                    return

        asyncio.create_task(ping_loop())

    def _stop_ping_interval(self) -> None:
        """Stop ping interval."""
        if self._ping_interval:
            self._ping_interval.cancel()
            self._ping_interval = None

    def _start_keepalive_interval(self) -> None:
        """Start periodic keep-alive data frames to reset proxy idle timers."""
        import os

        # In CCR sessions, session activity heartbeats handle keep-alives
        if os.environ.get("CLAUDE_CODE_REMOTE"):
            return

        self._stop_keepalive_interval()

        async def keepalive_loop() -> None:
            while self._state == WebSocketTransportState.CONNECTED:
                await asyncio.sleep(DEFAULT_KEEPALIVE_INTERVAL)
                if self._state != WebSocketTransportState.CONNECTED:
                    break
                try:
                    await self._send_line(KEEP_ALIVE_FRAME)
                except Exception as e:
                    logger.debug(
                        "WebSocketTransport: Periodic keep_alive failed: %s", e
                    )

        asyncio.create_task(keepalive_loop())

    def _stop_keepalive_interval(self) -> None:
        """Stop keepalive interval."""
        if self._keepalive_interval:
            self._keepalive_interval.cancel()
            self._keepalive_interval = None


# =============================================================================
# Hybrid Transport (v1)
# =============================================================================


@dataclass
class HybridTransport:
    """Hybrid transport: WebSocket for reads, HTTP POST for writes.

    Wraps WebSocketTransport for the bridge v1 adapter.
    Provides write batching and buffering similar to the TypeScript
    HybridTransport implementation.

    TypeScript equivalent: src/cli/transports/HybridTransport.ts
    """

    url: str
    headers: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None

    _ws_transport: WebSocketTransport | None = field(
        default=None, init=False, repr=False
    )
    _write_buffer: list[dict[str, Any]] = field(
        default_factory=list, init=False, repr=False
    )
    _flush_timer: asyncio.TimerHandle | None = field(
        default=None, init=False, repr=False
    )
    _last_sent_id: str | None = field(default=None, init=False, repr=False)
    _on_data: Callable[[str], None] | None = field(default=None, init=False)
    _on_close: Callable[[int | None], None] | None = field(default=None, init=False)
    _on_connect: Callable[[], None] | None = field(default=None, init=False)
    _dropped_batch_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the hybrid transport."""
        self._ws_transport = WebSocketTransport(
            url=self.url,
            headers=self.headers,
            session_id=self.session_id,
            auto_reconnect=True,
        )

    async def connect(self) -> None:
        """Connect the transport."""
        assert self._ws_transport is not None
        self._ws_transport.setOnData(self._on_data_wrapper)
        self._ws_transport.setOnClose(self._on_close_wrapper)
        self._ws_transport.setOnConnect(self._on_connect_wrapper)
        await self._ws_transport.connect()

    def _on_data_wrapper(self, data: str) -> None:
        """Handle inbound data."""
        if self._on_data:
            self._on_data(data)

    def _on_close_wrapper(self, close_code: int | None) -> None:
        """Handle close event."""
        if self._on_close:
            self._on_close(close_code)

    def _on_connect_wrapper(self) -> None:
        """Handle connect event."""
        if self._on_connect:
            self._on_connect()

    async def write(self, message: dict[str, Any]) -> None:
        """Write a message with buffering."""
        msg_uuid = message.get("uuid")
        if msg_uuid:
            self._last_sent_id = msg_uuid

        # Buffer for batched POST
        self._write_buffer.append(message)

        # Schedule flush
        loop = asyncio.get_running_loop()
        if self._flush_timer:
            self._flush_timer.cancel()
        self._flush_timer = loop.call_later(0.1, lambda: asyncio.create_task(self._flush()))

        # Also send via WebSocket
        assert self._ws_transport is not None
        await self._ws_transport.write(message)

    async def _flush(self) -> None:
        """Flush write buffer via HTTP POST."""
        if not self._write_buffer:
            return
        buffer = self._write_buffer
        self._write_buffer = []
        # TODO: HTTP POST via SerialBatchEventUploader
        logger.debug(
            "HybridTransport: Flushed %d messages (POST not yet implemented)",
            len(buffer),
        )

    async def writeBatch(self, messages: list[dict[str, Any]]) -> None:
        """Write multiple messages."""
        for msg in messages:
            await self.write(msg)

    def close(self) -> None:
        """Close the transport."""
        if self._flush_timer:
            self._flush_timer.cancel()
        if self._ws_transport:
            self._ws_transport.close()

    def isConnectedStatus(self) -> bool:
        """Check if connected."""
        if self._ws_transport:
            return self._ws_transport.isConnectedStatus()
        return False

    def getStateLabel(self) -> str:
        """Get state label."""
        if self._ws_transport:
            return self._ws_transport.getStateLabel()
        return WebSocketTransportState.CLOSED

    def setOnData(self, callback: Callable[[str], None]) -> None:
        """Register data callback."""
        self._on_data = callback

    def setOnClose(self, callback: Callable[[int | None], None]) -> None:
        """Register close callback."""
        self._on_close = callback

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        """Register connect callback."""
        self._on_connect = callback

    @property
    def droppedBatchCount(self) -> int:
        """Count of dropped batches."""
        return self._dropped_batch_count


# =============================================================================
# V1 Repl Transport Adapter
# =============================================================================


class V1ReplTransport:
    """V1 adapter wrapping HybridTransport for the ReplBridge interface.

    TypeScript equivalent: createV1ReplTransport() in replBridgeTransport.ts

    The HybridTransport already has the full surface (it wraps
    WebSocketTransport which has setOnConnect + getStateLabel). This is a
    wrapper that adapts it to the BridgeTransport protocol.
    """

    def __init__(self, hybrid: HybridTransport) -> None:
        """Initialize with a HybridTransport.

        Args:
            hybrid: The HybridTransport to wrap.
        """
        self._hybrid = hybrid
        self._on_data: Callable[[str], None] | None = None
        self._on_close: Callable[[int | None], None] | None = None
        self._on_connect: Callable[[], None] | None = None

        # Wire callbacks through
        self._hybrid.setOnData(self._on_data_wrapper)
        self._hybrid.setOnClose(self._on_close_wrapper)
        self._hybrid.setOnConnect(self._on_connect_wrapper)

    def _on_data_wrapper(self, data: str) -> None:
        if self._on_data:
            self._on_data(data)

    def _on_close_wrapper(self, close_code: int | None) -> None:
        if self._on_close:
            self._on_close(close_code)

    def _on_connect_wrapper(self) -> None:
        if self._on_connect:
            self._on_connect()

    def write(self, message: dict[str, Any]) -> None:
        """Write a message."""
        asyncio.create_task(self._hybrid.write(message))

    def writeBatch(self, messages: list[dict[str, Any]]) -> None:
        """Write multiple messages."""
        asyncio.create_task(self._hybrid.writeBatch(messages))

    def close(self) -> None:
        """Close the transport."""
        self._hybrid.close()

    def isConnectedStatus(self) -> bool:
        """Check if connected."""
        return self._hybrid.isConnectedStatus()

    def getStateLabel(self) -> str:
        """Get state label."""
        return self._hybrid.getStateLabel()

    def setOnData(self, callback: Callable[[str], None]) -> None:
        """Register data callback."""
        self._on_data = callback

    def setOnClose(self, callback: Callable[[int | None], None]) -> None:
        """Register close callback."""
        self._on_close = callback

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        """Register connect callback."""
        self._on_connect = callback

    def connect(self) -> None:
        """Initiate connection."""
        asyncio.create_task(self._hybrid.connect())

    def getLastSequenceNum(self) -> int:
        """Get last sequence number.

        V1 Session-Ingress WS doesn't use SSE sequence numbers;
        replay semantics are different. Always return 0.
        """
        return 0

    @property
    def droppedBatchCount(self) -> int:
        """Count of dropped batches."""
        return self._hybrid.droppedBatchCount

    def reportState(self, state: str) -> None:
        """Report state (v1 is no-op)."""
        pass

    def reportMetadata(self, metadata: dict[str, Any]) -> None:
        """Report metadata (v1 is no-op)."""
        pass

    def reportDelivery(
        self, event_id: str, status: str
    ) -> None:
        """Report delivery (v1 is no-op)."""
        pass

    def flush(self) -> None:
        """Flush (v1 resolves immediately)."""
        pass


# =============================================================================
# V2 Repl Transport Adapter
# =============================================================================


@dataclass
class V2ReplTransport:
    """V2 adapter: SSETransport (reads) + HTTP client (writes).

    Wraps SSE-based reading and CCR HTTP client for writes, state, and
    delivery tracking.

    TypeScript equivalent: createV2ReplTransport() in replBridgeTransport.ts

    Auth: v2 endpoints validate the JWT's session_id claim and worker role.
    The JWT is refreshed when the poll loop re-dispatches work.

    Attributes:
        session_url: Base URL for the session.
        ingress_token: Ingress token for auth.
        session_id: Session identifier.
        initial_sequence_num: SSE sequence-number high-water mark from previous transport.
        epoch: Worker epoch from POST /bridge response.
        heartbeat_interval_ms: CCRClient heartbeat interval.
        outbound_only: Skip opening the SSE read stream.
        get_auth_token: Optional per-instance auth header source.
    """

    session_url: str
    ingress_token: str
    session_id: str
    initial_sequence_num: int | None = None
    epoch: int | None = None
    heartbeat_interval_ms: int | None = None
    outbound_only: bool = False
    get_auth_token: Callable[[], str | None] | None = None

    # Internal state
    _closed: bool = field(default=False, init=False, repr=False)
    _ccr_initialized: bool = field(default=False, init=False, repr=False)
    _sse_transport: SSETransport | None = field(default=None, init=False, repr=False)
    _on_data: Callable[[str], None] | None = field(default=None, init=False)
    _on_close: Callable[[int | None], None] | None = field(default=None, init=False)
    _on_connect: Callable[[], None] | None = field(default=None, init=False)

    def write(self, message: dict[str, Any]) -> None:
        """Write a message via CCRClient HTTP POST."""
        if self._closed:
            return
        # TODO: CCRClient.writeEvent() via SerialBatchEventUploader
        logger.debug("V2ReplTransport: write() not yet implemented")

    def writeBatch(self, messages: list[dict[str, Any]]) -> None:
        """Write multiple messages in sequence (fire-and-forget async).

        SerialBatchEventUploader already batches internally (maxBatchSize=100);
        sequential enqueue preserves order and the uploader coalesces.
        """
        for msg in messages:
            if self._closed:
                break
            self._write_single(msg)

    def _write_single(self, message: dict[str, Any]) -> None:
        """Write a single message (fire-and-forget async)."""
        # TODO: CCRClient.writeEvent()
        logger.debug("V2ReplTransport: _write_single() not yet implemented")
        asyncio.create_task(self._async_write_single(message))

    async def _async_write_single(self, message: dict[str, Any]) -> None:
        """Async implementation of single message write."""
        # TODO: CCRClient.writeEvent()

    def close(self) -> None:
        """Close the transport and all resources."""
        self._closed = True
        if self._sse_transport:
            self._sse_transport.close()
            self._sse_transport = None

    def isConnectedStatus(self) -> bool:
        """Check if connected for writes (write-readiness, not read-readiness)."""
        return self._ccr_initialized

    def getStateLabel(self) -> str:
        """Get state label for debugging."""
        if self._sse_transport and self._sse_transport.isClosedStatus():
            return "closed"
        if self._sse_transport and self._sse_transport.isConnectedStatus():
            return "connected" if self._ccr_initialized else "init"
        return "connecting"

    def setOnData(self, callback: Callable[[str], None]) -> None:
        """Register data callback."""
        self._on_data = callback

    def setOnClose(self, callback: Callable[[int | None], None]) -> None:
        """Register close callback."""
        self._on_close = callback

    def setOnConnect(self, callback: Callable[[], None]) -> None:
        """Register connect callback."""
        self._on_connect = callback

    def getLastSequenceNum(self) -> int:
        """Get SSE sequence-number high-water mark."""
        if self._sse_transport:
            return self._sse_transport.getLastSequenceNum()
        return self.initial_sequence_num or 0

    @property
    def droppedBatchCount(self) -> int:
        """V2 write path doesn't set maxConsecutiveFailures — no drops."""
        return 0

    def reportState(self, state: str) -> None:
        """PUT /worker state via CCRClient."""
        # TODO: CCRClient.reportState()
        logger.debug("V2ReplTransport: reportState() not yet implemented")

    def reportMetadata(self, metadata: dict[str, Any]) -> None:
        """PUT /worker external_metadata via CCRClient."""
        # TODO: CCRClient.reportMetadata()
        logger.debug("V2ReplTransport: reportMetadata() not yet implemented")

    def reportDelivery(self, event_id: str, status: str) -> None:
        """POST /worker/events/{id}/delivery via CCRClient."""
        # TODO: CCRClient.reportDelivery()
        logger.debug("V2ReplTransport: reportDelivery() not yet implemented")

    def flush(self) -> None:
        """Drain the write queue before close (fire-and-forget)."""
        # TODO: CCRClient.flush()
        logger.debug("V2ReplTransport: flush() not yet implemented")

    def connect(self) -> None:
        """Initiate connection (fire-and-forget async).

        Opens SSE read stream (if not outbound-only) and initializes CCRClient.
        onConnect fires once CCRClient initializes.
        """
        asyncio.create_task(self._async_connect())

    async def _async_connect(self) -> None:
        """Internal async connection setup."""
        import os

        # Auth header builder
        auth_headers: Callable[[], dict[str, str]]
        if self.get_auth_token:

            def build_headers() -> dict[str, str]:
                token = self.get_auth_token()  # type: ignore
                if not token:
                    return {}
                return {"Authorization": f"Bearer {token}"}

            auth_headers = build_headers
        else:
            # Set process-wide env var for legacy single-session path
            os.environ["CLAUDE_CODE_SESSION_ACCESS_TOKEN"] = self.ingress_token

            def build_headers() -> dict[str, str]:
                return {"Authorization": f"Bearer {self.ingress_token}"}

            auth_headers = build_headers

        # Register worker (get epoch)
        epoch = self.epoch
        if epoch is None:
            # TODO: registerWorker() call
            epoch = 0
            logger.debug(
                "V2ReplTransport: Worker sessionId=%s epoch=%d "
                "(registerWorker not yet implemented)",
                self.session_id,
                epoch,
            )

        # Derive SSE stream URL
        sse_url = self.session_url.rstrip("/") + "/worker/events/stream"

        if not self.outbound_only:
            self._sse_transport = SSETransport(
                url=sse_url,
                headers={},
                session_id=self.session_id,
                from_sequence_num=self.initial_sequence_num,
                get_auth_headers=auth_headers,
            )
            self._sse_transport.setOnData(self._on_sse_data)
            self._sse_transport.setOnClose(self._on_sse_close)
            asyncio.create_task(self._sse_transport.connect())

        # Initialize CCRClient
        # TODO: CCRClient.initialize() and heartbeat
        logger.debug(
            "V2ReplTransport: connect() — SSE and CCRClient not yet fully implemented"
        )
        # Simulate successful init
        self._ccr_initialized = True
        if self._on_connect:
            self._on_connect()

    def _on_sse_data(self, data: str) -> None:
        """Handle SSE data."""
        if self._on_data:
            self._on_data(data)

    def _on_sse_close(self, close_code: int | None) -> None:
        """Handle SSE close."""
        if self._on_close:
            self._on_close(close_code or 4092)


# =============================================================================
# SSE Transport (for v2)
# =============================================================================


@dataclass
class SSETransport:
    """SSE (Server-Sent Events) transport for reading.

    Connects to an SSE endpoint and delivers events via callbacks.
    Handles sequence numbers for resumable connections.

    TypeScript equivalent: src/cli/transports/SSETransport.ts

    Attributes:
        url: SSE stream URL.
        headers: HTTP headers.
        session_id: Session identifier.
        from_sequence_num: Resume from this sequence number.
        get_auth_headers: Optional auth header builder.
    """

    url: str
    headers: dict[str, str] = field(default_factory=dict)
    session_id: str | None = None
    from_sequence_num: int | None = None
    get_auth_headers: Callable[[], dict[str, str]] | None = None

    _on_data: Callable[[str], None] | None = field(default=None, init=False)
    _on_close: Callable[[int | None], None] | None = field(default=None, init=False)
    _on_event: Callable[[dict[str, Any]], None] | None = field(default=None, init=False)
    _state: str = field(default=WebSocketTransportState.IDLE, init=False)
    _last_sequence_num: int = field(default=0, init=False)
    _buffer: str = field(default="", init=False)
    _event_id: str | None = field(default=None, init=False)

    def setOnData(self, callback: Callable[[str], None]) -> None:
        """Register data callback."""
        self._on_data = callback

    def setOnClose(self, callback: Callable[[int | None], None]) -> None:
        """Register close callback."""
        self._on_close = callback

    def setOnEvent(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register event callback (replaces previous)."""
        self._on_event = callback

    def isConnectedStatus(self) -> bool:
        """Check if SSE stream is connected."""
        return self._state == WebSocketTransportState.CONNECTED

    def isClosedStatus(self) -> bool:
        """Check if SSE stream is closed."""
        return self._state == WebSocketTransportState.CLOSED

    def getLastSequenceNum(self) -> int:
        """Get the high-water mark of sequence numbers seen."""
        # Use from_sequence_num as initial value until first event updates it
        if self._last_sequence_num == 0 and self.from_sequence_num is not None:
            return self.from_sequence_num
        return self._last_sequence_num

    async def connect(self) -> None:
        """Connect to the SSE endpoint."""

        self._state = WebSocketTransportState.RECONNECTING

        headers = dict(self.headers)
        if self.get_auth_headers:
            headers.update(self.get_auth_headers())

        # Add Last-Event-ID header for resumption
        if self.from_sequence_num is not None:
            headers["Last-Event-ID"] = str(self.from_sequence_num)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session, session.request(
                "GET", self.url, headers=headers, timeout=aiohttp.ClientTimeout()
            ) as response:
                self._state = WebSocketTransportState.CONNECTED
                async for line in response.content:
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    self._process_sse_line(decoded)

                self._state = WebSocketTransportState.CLOSED
                if self._on_close:
                    self._on_close(response.status)
        except Exception as e:
            logger.debug("SSETransport: Connection error: %s", e)
            self._state = WebSocketTransportState.CLOSED
            if self._on_close:
                self._on_close(None)

    def _process_sse_line(self, line: str) -> None:
        """Process a single SSE line.

        Implements the SSE event stream format:
        - field:value lines
        - blank line terminates an event
        - Lines starting with : are comments

        Args:
            line: A single line from the SSE stream.
        """
        if not line:
            # Blank line — dispatch event
            if self._buffer or self._event_id:
                # Strip trailing newline from accumulated buffer
                event_data = self._buffer.rstrip("\n")
                self._buffer = ""

                # Extract sequence number from id field
                event_id = self._event_id
                self._event_id = None

                if event_id:
                    try:
                        seq = int(event_id)
                        if seq > self._last_sequence_num:
                            self._last_sequence_num = seq
                    except ValueError:
                        pass

                # Dispatch
                if self._on_data:
                    self._on_data(event_data)
                if self._on_event:
                    self._on_event({
                        "event_id": event_id,
                        "data": event_data,
                    })
            return

        # Comment line
        if line.startswith(":"):
            return

        # Field:value
        if ":" in line:
            field_name, field_value = line.split(":", 1)
            field_name = field_name.strip()
            field_value = field_value.lstrip()

            if field_name == "id":
                self._event_id = field_value
            elif field_name == "data":
                self._buffer += field_value + "\n"
            elif field_name == "event":
                # Event type
                pass
            elif field_name == "retry":
                # Reconnection time
                pass
        else:
            # continuation
            self._buffer += line + "\n"

    def close(self) -> None:
        """Close the SSE transport."""
        self._state = WebSocketTransportState.CLOSED


# =============================================================================
# Factory Functions
# =============================================================================


def create_v1_repl_transport(
    hybrid: HybridTransport,
) -> BridgeTransport:
    """Create a v1 ReplBridgeTransport wrapping HybridTransport.

    TypeScript equivalent: createV1ReplTransport()

    V1 uses HybridTransport (WebSocket reads + HTTP POST writes to
    Session-Ingress). The HybridTransport already has the full surface.

    Args:
        hybrid: The HybridTransport to wrap.

    Returns:
        A BridgeTransport adapter for v1.
    """
    return V1ReplTransport(hybrid)


def create_v2_repl_transport(
    session_url: str,
    ingress_token: str,
    session_id: str,
    initial_sequence_num: int | None = None,
    epoch: int | None = None,
    heartbeat_interval_ms: int | None = None,
    outbound_only: bool = False,
    get_auth_token: Callable[[], str | None] | None = None,
) -> BridgeTransport:
    """Create a v2 ReplBridgeTransport with SSE + HTTP client.

    TypeScript equivalent: createV2ReplTransport()

    V2 uses SSETransport (reads) + CCRClient (writes to CCR v2 /worker/*).

    Auth: v2 endpoints validate the JWT's session_id claim and worker role.
    The JWT is refreshed when the poll loop re-dispatches work — callers
    invoke this factory again with the fresh token.

    Args:
        session_url: Base URL for the session.
        ingress_token: Ingress token for auth.
        session_id: Session identifier.
        initial_sequence_num: SSE sequence-number high-water mark from previous transport.
        epoch: Worker epoch from POST /bridge response.
        heartbeat_interval_ms: CCRClient heartbeat interval.
        outbound_only: Skip opening the SSE read stream.
        get_auth_token: Optional per-instance auth header source.

    Returns:
        A BridgeTransport adapter for v2.
    """
    transport = V2ReplTransport(
        session_url=session_url,
        ingress_token=ingress_token,
        session_id=session_id,
        initial_sequence_num=initial_sequence_num,
        epoch=epoch,
        heartbeat_interval_ms=heartbeat_interval_ms,
        outbound_only=outbound_only,
        get_auth_token=get_auth_token,
    )
    transport.connect()
    return transport
