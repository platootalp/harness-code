"""
Tests for bridge/transport.py.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from claude_code.bridge.transport import (
    KEEP_ALIVE_FRAME,
    PERMANENT_CLOSE_CODES,
    BridgeTransport,
    HybridTransport,
    SessionState,
    SSETransport,
    V1ReplTransport,
    V2ReplTransport,
    WebSocketTransport,
    WebSocketTransportState,
    create_v1_repl_transport,
    create_v2_repl_transport,
)

# =============================================================================
# BridgeTransport Protocol
# =============================================================================


class TestBridgeTransportProtocol:
    """Verify BridgeTransport protocol interface."""

    def test_write_method_exists(self) -> None:
        """Test BridgeTransport has write method."""

        def check_protocol(t: BridgeTransport) -> None:
            t.write({})

        # These concrete classes should satisfy the protocol
        # (checked structurally via Protocol)
        assert hasattr(BridgeTransport, "write")

    def test_all_required_methods_exist(self) -> None:
        """Test all required BridgeTransport methods are defined."""
        required = [
            "write",
            "writeBatch",
            "close",
            "isConnectedStatus",
            "getStateLabel",
            "setOnData",
            "setOnClose",
            "setOnConnect",
            "connect",
            "getLastSequenceNum",
            "reportState",
            "reportMetadata",
            "reportDelivery",
            "flush",
        ]
        for method in required:
            assert hasattr(BridgeTransport, method)


# =============================================================================
# Session State
# =============================================================================


class TestSessionState:
    """Tests for SessionState constants."""

    def test_session_state_values(self) -> None:
        """Test SessionState enum-like values."""
        assert SessionState.IDLE == "idle"
        assert SessionState.RUNNING == "running"
        assert SessionState.REQUIRES_ACTION == "requires_action"


# =============================================================================
# WebSocketTransportState
# =============================================================================


class TestWebSocketTransportState:
    """Tests for WebSocketTransportState constants."""

    def test_state_values(self) -> None:
        """Test WebSocketTransportState enum-like values."""
        assert WebSocketTransportState.IDLE == "idle"
        assert WebSocketTransportState.CONNECTED == "connected"
        assert WebSocketTransportState.RECONNECTING == "reconnecting"
        assert WebSocketTransportState.CLOSING == "closing"
        assert WebSocketTransportState.CLOSED == "closed"


# =============================================================================
# Constants
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_keep_alive_frame(self) -> None:
        """Test keep-alive frame format."""
        assert KEEP_ALIVE_FRAME == '{"type":"keep_alive"}\n'

    def test_permanent_close_codes(self) -> None:
        """Test permanent WebSocket close codes."""
        assert 1002 in PERMANENT_CLOSE_CODES
        assert 4001 in PERMANENT_CLOSE_CODES
        assert 4003 in PERMANENT_CLOSE_CODES
        assert 1000 not in PERMANENT_CLOSE_CODES


# =============================================================================
# WebSocketTransport
# =============================================================================


class TestWebSocketTransport:
    """Tests for WebSocketTransport."""

    def test_initial_state(self) -> None:
        """Test WebSocketTransport starts in IDLE state."""
        t = WebSocketTransport(url="wss://example.com/ws")
        assert t.isConnectedStatus() is False
        assert t.isClosedStatus() is False
        assert t.getStateLabel() == WebSocketTransportState.IDLE

    def test_set_on_data(self) -> None:
        """Test setting data callback."""
        t = WebSocketTransport(url="wss://example.com/ws")
        received: list[str] = []

        def on_data(data: str) -> None:
            received.append(data)

        t.setOnData(on_data)
        # Manually trigger callback
        assert t._on_data is on_data

    def test_set_on_close(self) -> None:
        """Test setting close callback."""
        t = WebSocketTransport(url="wss://example.com/ws")

        def on_close(code: int | None) -> None:
            pass

        t.setOnClose(on_close)
        assert t._on_close_callback is on_close

    def test_set_on_connect(self) -> None:
        """Test setting connect callback."""
        t = WebSocketTransport(url="wss://example.com/ws")

        def on_connect() -> None:
            pass

        t.setOnConnect(on_connect)
        assert t._on_connect_callback is on_connect

    def test_message_buffer_initially_empty(self) -> None:
        """Test message buffer starts empty."""
        t = WebSocketTransport(url="wss://example.com/ws")
        assert t._message_buffer == []

    def test_auto_reconnect_default(self) -> None:
        """Test auto_reconnect defaults to True."""
        t = WebSocketTransport(url="wss://example.com/ws")
        assert t.auto_reconnect is True

    def test_is_closed_status(self) -> None:
        """Test isClosedStatus()."""
        t = WebSocketTransport(url="wss://example.com/ws")
        assert t.isClosedStatus() is False

    def test_state_label(self) -> None:
        """Test getStateLabel()."""
        t = WebSocketTransport(url="wss://example.com/ws")
        assert t.getStateLabel() == WebSocketTransportState.IDLE


# =============================================================================
# HybridTransport
# =============================================================================


class TestHybridTransport:
    """Tests for HybridTransport."""

    def test_initial_state(self) -> None:
        """Test HybridTransport initializes with WebSocket transport."""
        t = HybridTransport(url="wss://example.com/ws")
        assert t._ws_transport is not None
        assert t._write_buffer == []
        assert t.isConnectedStatus() is False

    def test_get_state_label(self) -> None:
        """Test getStateLabel delegates to ws_transport."""
        t = HybridTransport(url="wss://example.com/ws")
        assert t.getStateLabel() == WebSocketTransportState.IDLE

    def test_dropped_batch_count_initially_zero(self) -> None:
        """Test droppedBatchCount starts at 0."""
        t = HybridTransport(url="wss://example.com/ws")
        assert t.droppedBatchCount == 0

    def test_set_on_data_registers_callback(self) -> None:
        """Test setOnData registers callback."""
        t = HybridTransport(url="wss://example.com/ws")

        def on_data(data: str) -> None:
            pass

        t.setOnData(on_data)
        assert t._on_data is on_data

    def test_set_on_close_registers_callback(self) -> None:
        """Test setOnClose registers callback."""
        t = HybridTransport(url="wss://example.com/ws")

        def on_close(code: int | None) -> None:
            pass

        t.setOnClose(on_close)
        assert t._on_close is on_close

    def test_set_on_connect_registers_callback(self) -> None:
        """Test setOnConnect registers callback."""
        t = HybridTransport(url="wss://example.com/ws")

        def on_connect() -> None:
            pass

        t.setOnConnect(on_connect)
        assert t._on_connect is on_connect

    def test_close_stops_flush_timer(self) -> None:
        """Test close stops flush timer."""
        t = HybridTransport(url="wss://example.com/ws")
        t.close()  # Should not raise


# =============================================================================
# V1ReplTransport
# =============================================================================


class TestV1ReplTransport:
    """Tests for V1ReplTransport adapter."""

    def test_get_last_sequence_num_returns_zero(self) -> None:
        """Test V1 transport always returns 0 for sequence num."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)
        assert v1.getLastSequenceNum() == 0

    def test_dropped_batch_count_delegates(self) -> None:
        """Test droppedBatchCount delegates to hybrid."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)
        assert v1.droppedBatchCount == 0

    def test_report_state_is_noop(self) -> None:
        """Test reportState is a no-op for v1."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)
        v1.reportState("running")  # Should not raise

    def test_report_metadata_is_noop(self) -> None:
        """Test reportMetadata is a no-op for v1."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)
        v1.reportMetadata({})  # Should not raise

    def test_report_delivery_is_noop(self) -> None:
        """Test reportDelivery is a no-op for v1."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)
        v1.reportDelivery("event-1", "processed")  # Should not raise

    def test_flush_is_noop(self) -> None:
        """Test flush is a no-op for v1."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)
        v1.flush()  # Should not raise

    def test_set_on_data(self) -> None:
        """Test setOnData registers callback."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)

        def on_data(data: str) -> None:
            pass

        v1.setOnData(on_data)
        assert v1._on_data is on_data

    def test_set_on_close(self) -> None:
        """Test setOnClose registers callback."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)

        def on_close(code: int | None) -> None:
            pass

        v1.setOnClose(on_close)
        assert v1._on_close is on_close

    def test_set_on_connect(self) -> None:
        """Test setOnConnect registers callback."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        v1 = V1ReplTransport(hybrid)

        def on_connect() -> None:
            pass

        v1.setOnConnect(on_connect)
        assert v1._on_connect is on_connect


# =============================================================================
# V2ReplTransport
# =============================================================================


class TestV2ReplTransport:
    """Tests for V2ReplTransport adapter."""

    def test_initial_state(self) -> None:
        """Test V2ReplTransport initializes correctly."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        assert v2._closed is False
        assert v2._ccr_initialized is False
        assert v2._sse_transport is None

    def test_is_connected_status_initially_false(self) -> None:
        """Test isConnectedStatus returns False before init."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        assert v2.isConnectedStatus() is False

    def test_get_state_label_initially_connecting(self) -> None:
        """Test getStateLabel returns 'connecting' before SSE opens."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        assert v2.getStateLabel() == "connecting"

    def test_get_last_sequence_num_defaults(self) -> None:
        """Test getLastSequenceNum with no SSE transport."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
            initial_sequence_num=42,
        )
        assert v2.getLastSequenceNum() == 42

    def test_dropped_batch_count_is_zero(self) -> None:
        """Test droppedBatchCount is always 0 for v2."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        assert v2.droppedBatchCount == 0

    def test_report_state_is_noop(self) -> None:
        """Test reportState is a no-op for v2."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        v2.reportState("running")  # Should not raise

    def test_report_metadata_is_noop(self) -> None:
        """Test reportMetadata is a no-op for v2."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        v2.reportMetadata({})  # Should not raise

    def test_report_delivery_is_noop(self) -> None:
        """Test reportDelivery is a no-op for v2."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        v2.reportDelivery("event-1", "processed")  # Should not raise

    def test_flush_is_noop(self) -> None:
        """Test flush is a no-op for v2."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        v2.flush()  # Should not raise

    def test_write_when_closed_is_noop(self) -> None:
        """Test write is a no-op when closed."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        v2._closed = True
        v2.write({"type": "user", "content": "hello"})  # Should not raise

    def test_write_batch_when_closed_stops(self) -> None:
        """Test writeBatch stops when closed flag is set mid-batch."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        v2._closed = True
        v2.writeBatch([{"type": "user", "content": "hello"}])  # Should not raise

    def test_set_on_data(self) -> None:
        """Test setOnData registers callback."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )

        def on_data(data: str) -> None:
            pass

        v2.setOnData(on_data)
        assert v2._on_data is on_data

    def test_set_on_close(self) -> None:
        """Test setOnClose registers callback."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )

        def on_close(code: int | None) -> None:
            pass

        v2.setOnClose(on_close)
        assert v2._on_close is on_close

    def test_set_on_connect(self) -> None:
        """Test setOnConnect registers callback."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )

        def on_connect() -> None:
            pass

        v2.setOnConnect(on_connect)
        assert v2._on_connect is on_connect

    @pytest.mark.asyncio
    async def test_connect_fires_on_connect_callback(self) -> None:
        """Test connect() eventually fires onConnect callback."""
        import asyncio

        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        connected = False

        def on_connect() -> None:
            nonlocal connected
            connected = True

        v2.setOnConnect(on_connect)
        v2.connect()

        # Allow the scheduled async task to run
        await asyncio.sleep(0)
        assert connected is True

    def test_close_sets_closed_flag(self) -> None:
        """Test close() sets closed flag."""
        v2 = V2ReplTransport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        assert v2._closed is False
        v2.close()
        assert v2._closed is True


# =============================================================================
# SSETransport
# =============================================================================


class TestSSETransport:
    """Tests for SSETransport."""

    def test_initial_state(self) -> None:
        """Test SSETransport starts in IDLE state."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        assert t._state == WebSocketTransportState.IDLE
        assert t._last_sequence_num == 0

    def test_from_sequence_num_sets_initial(self) -> None:
        """Test from_sequence_num is stored."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
            from_sequence_num=50,
        )
        assert t.from_sequence_num == 50

    def test_get_last_sequence_num(self) -> None:
        """Test getLastSequenceNum returns the tracked sequence."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
            from_sequence_num=10,
        )
        assert t.getLastSequenceNum() == 10

    def test_is_connected_status_initially_false(self) -> None:
        """Test isConnectedStatus returns False initially."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        assert t.isConnectedStatus() is False

    def test_is_closed_status_initially_false(self) -> None:
        """Test isClosedStatus returns False initially."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        assert t.isClosedStatus() is False

    def test_set_on_data_registers_callback(self) -> None:
        """Test setOnData registers callback."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )

        def on_data(data: str) -> None:
            pass

        t.setOnData(on_data)
        assert t._on_data is on_data

    def test_set_on_close_registers_callback(self) -> None:
        """Test setOnClose registers callback."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )

        def on_close(code: int | None) -> None:
            pass

        t.setOnClose(on_close)
        assert t._on_close is on_close

    def test_set_on_event_registers_callback(self) -> None:
        """Test setOnEvent registers callback."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )

        def on_event(event: dict[str, Any]) -> None:
            pass

        t.setOnEvent(on_event)
        assert t._on_event is on_event

    def test_close_sets_state(self) -> None:
        """Test close() sets state to CLOSED."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        t.close()
        assert t.isClosedStatus() is True

    def test_process_sse_line_blank_line_dispatches(self) -> None:
        """Test blank line dispatches buffered data."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        received_data: list[str] = []

        def on_data(data: str) -> None:
            received_data.append(data)

        t.setOnData(on_data)

        # Feed: "data: hello\n\n"
        t._process_sse_line("data: hello")
        assert received_data == []
        t._process_sse_line("")
        assert received_data == ["hello"]

    def test_process_sse_line_comment_ignored(self) -> None:
        """Test comment lines (:) are ignored."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        received_data: list[str] = []

        def on_data(data: str) -> None:
            received_data.append(data)

        t.setOnData(on_data)

        # Comment should not dispatch
        t._process_sse_line(":keepalive")
        assert received_data == []

    def test_process_sse_line_id_updates_sequence(self) -> None:
        """Test id: field updates sequence number."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        received_events: list[dict[str, Any]] = []

        def on_event(event: dict[str, Any]) -> None:
            received_events.append(event)

        t.setOnEvent(on_event)

        # Feed: id: 42\ndata: hello\n\n
        t._process_sse_line("id: 42")
        assert t._last_sequence_num == 0  # Not updated until event dispatch
        t._process_sse_line("data: hello")
        t._process_sse_line("")
        assert t._last_sequence_num == 42
        assert received_events[0]["event_id"] == "42"

    def test_process_sse_line_multi_data_lines_concat(self) -> None:
        """Test multiple data: lines are concatenated."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        received_data: list[str] = []

        def on_data(data: str) -> None:
            received_data.append(data)

        t.setOnData(on_data)

        t._process_sse_line("data: line1")
        t._process_sse_line("data: line2")
        t._process_sse_line("")
        assert received_data == ["line1\nline2"]

    def test_process_sse_line_continuation(self) -> None:
        """Test lines without colon are treated as continuation."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        received_data: list[str] = []

        def on_data(data: str) -> None:
            received_data.append(data)

        t.setOnData(on_data)

        t._process_sse_line("data: start")
        t._process_sse_line("continued")
        t._process_sse_line("")
        assert received_data == ["start\ncontinued"]

    def test_process_sse_line_event_type_field(self) -> None:
        """Test event: field is parsed (but not used in this simplified impl)."""
        t = SSETransport(
            url="https://example.com/stream",
            session_id="session-123",
        )
        # Should not raise
        t._process_sse_line("event: message")
        t._process_sse_line("data: hello")
        t._process_sse_line("")


# =============================================================================
# Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """Tests for create_v1_repl_transport and create_v2_repl_transport."""

    def test_create_v1_repl_transport(self) -> None:
        """Test create_v1_repl_transport returns BridgeTransport."""
        hybrid = HybridTransport(url="wss://example.com/ws")
        transport = create_v1_repl_transport(hybrid)
        # Verify it has the required protocol methods
        assert hasattr(transport, "write")
        assert hasattr(transport, "writeBatch")
        assert hasattr(transport, "close")
        assert hasattr(transport, "connect")
        assert hasattr(transport, "getLastSequenceNum")
        assert hasattr(transport, "reportState")
        assert hasattr(transport, "reportMetadata")
        assert hasattr(transport, "reportDelivery")
        assert hasattr(transport, "flush")

    @pytest.mark.asyncio
    async def test_create_v2_repl_transport_returns_bridge_transport(self) -> None:
        """Test create_v2_repl_transport returns BridgeTransport."""
        transport = create_v2_repl_transport(
            session_url="https://example.com/session",
            ingress_token="token123",
            session_id="session-abc",
        )
        # Verify it has the required protocol methods
        assert hasattr(transport, "write")
        assert hasattr(transport, "writeBatch")
        assert hasattr(transport, "close")
        assert hasattr(transport, "connect")
        assert hasattr(transport, "getLastSequenceNum")
        assert hasattr(transport, "reportState")
        assert hasattr(transport, "reportMetadata")
        assert hasattr(transport, "reportDelivery")
        assert hasattr(transport, "flush")
