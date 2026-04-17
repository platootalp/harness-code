"""
Tests for bridge/debug.py - Bridge fault injection for testing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_code.bridge.api import BridgeFatalError


class TestBridgeDebugHandle:
    """Tests for BridgeDebugHandle type and related types."""

    def test_bridge_fault_type_creation(self) -> None:
        """BridgeFault should have required fields."""
        from claude_code.bridge.debug import BridgeFault

        fault = BridgeFault(
            method="pollForWork",
            kind="fatal",
            status=404,
            error_type="not_found_error",
            count=1,
        )
        assert fault.method == "pollForWork"
        assert fault.kind == "fatal"
        assert fault.status == 404
        assert fault.error_type == "not_found_error"
        assert fault.count == 1

    def test_bridge_fault_transient_kind(self) -> None:
        """BridgeFault supports transient kind."""
        from claude_code.bridge.debug import BridgeFault

        fault = BridgeFault(
            method="registerBridgeEnvironment",
            kind="transient",
            status=500,
            error_type=None,
            count=3,
        )
        assert fault.kind == "transient"
        assert fault.status == 500

    def test_bridge_debug_handle_fields(self) -> None:
        """BridgeDebugHandle should have expected methods."""
        from claude_code.bridge.debug import BridgeDebugHandle

        mock_close = MagicMock()
        mock_reconnect = MagicMock()
        mock_inject = MagicMock()
        mock_wake = MagicMock()
        mock_describe = MagicMock(return_value="bridge-123 / env-456")

        handle = BridgeDebugHandle(
            fire_close=mock_close,
            force_reconnect=mock_reconnect,
            inject_fault=mock_inject,
            wake_poll_loop=mock_wake,
            describe=mock_describe,
        )
        assert handle.describe() == "bridge-123 / env-456"
        mock_describe.assert_called_once()


class TestDebugModuleState:
    """Tests for module-level debug handle management."""

    def test_register_and_get(self) -> None:
        """registerBridgeDebugHandle / getBridgeDebugHandle roundtrip."""
        from claude_code.bridge.debug import (
            BridgeDebugHandle,
            clear_bridge_debug_handle,
            get_bridge_debug_handle,
            register_bridge_debug_handle,
        )

        clear_bridge_debug_handle()
        assert get_bridge_debug_handle() is None

        handle = BridgeDebugHandle(
            fire_close=MagicMock(),
            force_reconnect=MagicMock(),
            inject_fault=MagicMock(),
            wake_poll_loop=MagicMock(),
            describe=MagicMock(return_value="test"),
        )
        register_bridge_debug_handle(handle)
        assert get_bridge_debug_handle() is handle

        clear_bridge_debug_handle()
        assert get_bridge_debug_handle() is None

    def test_clear_resets_fault_queue(self) -> None:
        """clearBridgeDebugHandle resets both handle and fault queue."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            get_bridge_debug_handle,
            inject_bridge_fault,
        )

        clear_bridge_debug_handle()

        # Inject faults
        inject_bridge_fault(
            method="pollForWork",
            kind="fatal",
            status=404,
            error_type="not_found",
            count=1,
        )
        inject_bridge_fault(
            method="heartbeatWork",
            kind="transient",
            status=500,
            error_type=None,
            count=2,
        )

        # Verify they were queued (fault queue is internal, but clear resets)
        clear_bridge_debug_handle()
        assert get_bridge_debug_handle() is None


class TestInjectBridgeFault:
    """Tests for inject_bridge_fault()."""

    def test_inject_fault_with_all_fields(self) -> None:
        """inject_bridge_fault should queue a fault with all fields."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
        )

        clear_bridge_debug_handle()
        inject_bridge_fault(
            method="pollForWork",
            kind="fatal",
            status=404,
            error_type="not_found_error",
            count=3,
        )
        # No exception means success

    def test_inject_fault_transient(self) -> None:
        """inject_bridge_fault supports transient kind."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
        )

        clear_bridge_debug_handle()
        inject_bridge_fault(
            method="registerBridgeEnvironment",
            kind="transient",
            status=503,
            error_type=None,
            count=1,
        )

    def test_inject_multiple_faults(self) -> None:
        """Multiple faults can be queued."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
        )

        clear_bridge_debug_handle()
        for i in range(5):
            inject_bridge_fault(
                method="pollForWork",
                kind="fatal",
                status=404 + i,
                error_type=None,
                count=1,
            )


class TestWrapApiForFaultInjection:
    """Tests for wrap_api_for_fault_injection()."""

    def test_unmocked_call_passes_through(self) -> None:
        """Calls without injected faults pass through to the real API."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            wrap_api_for_fault_injection,
        )

        clear_bridge_debug_handle()

        mock_api = MagicMock()
        mock_api.poll_for_work = AsyncMock(return_value={"work": "data"})
        mock_api.register_bridge_environment = AsyncMock(
            return_value={"envId": "e1"}
        )

        wrapped = wrap_api_for_fault_injection(mock_api)

        # Call without any faults injected
        result = wrapped.poll_for_work("env1", "secret", None, 5000)
        # result is a coroutine
        import asyncio

        val = asyncio.get_event_loop().run_until_complete(result)
        assert val == {"work": "data"}
        mock_api.poll_for_work.assert_called_once()

    def test_injected_fatal_fault_raises_bridge_fatal_error(self) -> None:
        """Fatal fault injection throws BridgeFatalError."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
            wrap_api_for_fault_injection,
        )

        clear_bridge_debug_handle()

        mock_api = MagicMock()
        mock_api.poll_for_work = AsyncMock(return_value={"work": "data"})

        wrapped = wrap_api_for_fault_injection(mock_api)

        inject_bridge_fault(
            method="pollForWork",
            kind="fatal",
            status=404,
            error_type="not_found_error",
            count=1,
        )

        import asyncio

        with pytest.raises(BridgeFatalError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                wrapped.poll_for_work("env1", "secret", None, 5000)
            )
        assert exc_info.value.status == 404
        assert exc_info.value.error_type == "not_found_error"
        # Real API should NOT have been called
        mock_api.poll_for_work.assert_not_called()

    def test_injected_transient_fault_raises_error(self) -> None:
        """Transient fault injection throws a plain RuntimeError."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
            wrap_api_for_fault_injection,
        )

        clear_bridge_debug_handle()

        mock_api = MagicMock()
        mock_api.register_bridge_environment = AsyncMock(return_value={})

        wrapped = wrap_api_for_fault_injection(mock_api)

        inject_bridge_fault(
            method="registerBridgeEnvironment",
            kind="transient",
            status=503,
            error_type=None,
            count=1,
        )

        import asyncio

        with pytest.raises(RuntimeError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                wrapped.register_bridge_environment({})
            )
        assert "503" in str(exc_info.value)
        # Real API should NOT have been called
        mock_api.register_bridge_environment.assert_not_called()

    def test_fault_count_decrements(self) -> None:
        """Fault count decrements on each matching call."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
            wrap_api_for_fault_injection,
        )

        clear_bridge_debug_handle()

        mock_api = MagicMock()
        mock_api.heartbeat_work = AsyncMock(return_value={})

        wrapped = wrap_api_for_fault_injection(mock_api)

        inject_bridge_fault(
            method="heartbeatWork",
            kind="fatal",
            status=408,
            error_type="timeout",
            count=2,
        )

        import asyncio

        # First call — should inject fault
        with pytest.raises(BridgeFatalError):
            asyncio.get_event_loop().run_until_complete(
                wrapped.heartbeat_work("env1", "work1", "token")
            )

        # Second call — fault should still be there (count was 2)
        with pytest.raises(BridgeFatalError):
            asyncio.get_event_loop().run_until_complete(
                wrapped.heartbeat_work("env1", "work1", "token")
            )

        # Third call — fault exhausted, goes through to real API
        asyncio.get_event_loop().run_until_complete(
            wrapped.heartbeat_work("env1", "work1", "token")
        )
        assert mock_api.heartbeat_work.call_count == 1

    def test_fault_method_specific(self) -> None:
        """Fault injection only affects the named method."""
        from claude_code.bridge.debug import (
            clear_bridge_debug_handle,
            inject_bridge_fault,
            wrap_api_for_fault_injection,
        )

        clear_bridge_debug_handle()

        mock_api = MagicMock()
        mock_api.poll_for_work = AsyncMock(return_value={"work": "data"})
        mock_api.reconnect_session = AsyncMock(return_value={})

        wrapped = wrap_api_for_fault_injection(mock_api)

        # Only inject fault for reconnectSession
        inject_bridge_fault(
            method="reconnectSession",
            kind="fatal",
            status=404,
            error_type="not_found",
            count=1,
        )

        import asyncio

        # pollForWork should pass through
        val = asyncio.get_event_loop().run_until_complete(
            wrapped.poll_for_work("env1", "secret", None, 5000)
        )
        assert val == {"work": "data"}
        assert mock_api.poll_for_work.call_count == 1

        # reconnectSession should be faulted
        with pytest.raises(BridgeFatalError):
            asyncio.get_event_loop().run_until_complete(
                wrapped.reconnect_session("env1", "sess1")
            )
