"""Bridge fault injection for manual testing of recovery paths.

Ant-only fault injection for manually testing bridge recovery paths.
Real failure modes this targets:
  - poll 404 not_found_error — dead onEnvironmentLost gate
  - ws_closed 1002/1006 — zombie poll after close
  - register transient failure — network blips during doReconnect

Usage: /bridge-kick <subcommand> from the REPL while Remote Control is
connected, then tail debug.log to watch the recovery machinery react.

TypeScript equivalent: src/bridge/bridgeDebug.ts
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    pass

# =============================================================================
# Types
# =============================================================================


class BridgeFaultKind(StrEnum):
    """Kind of fault to inject."""

    FATAL = "fatal"
    TRANSIENT = "transient"


class BridgeFaultMethod(StrEnum):
    """API method to inject fault into."""

    POLL_FOR_WORK = "pollForWork"
    REGISTER_BRIDGE_ENVIRONMENT = "registerBridgeEnvironment"
    RECONNECT_SESSION = "reconnectSession"
    HEARTBEAT_WORK = "heartbeatWork"


@dataclass
class BridgeFault:
    """One-shot fault to inject on the next matching API call."""

    method: BridgeFaultMethod | str
    kind: BridgeFaultKind | str
    status: int
    error_type: str | None = None
    count: int = 1


@dataclass
class BridgeDebugHandle:
    """Handle for bridge debug operations."""

    fire_close: Callable[[int], None]
    force_reconnect: Callable[[], None]
    inject_fault: Callable[[BridgeFault], None]
    wake_poll_loop: Callable[[], None]
    describe: Callable[[], str]


# =============================================================================
# Module-level state
# =============================================================================

_debug_handle: BridgeDebugHandle | None = None
_fault_queue: list[BridgeFault] = []


def _log_for_debugging(msg: str) -> None:
    """Debug logging stub."""
    # Stub: in production would call real log utility
    pass


# =============================================================================
# Public API
# =============================================================================


def register_bridge_debug_handle(h: BridgeDebugHandle) -> None:
    """Register a bridge debug handle.

    Args:
        h: BridgeDebugHandle instance.
    """
    global _debug_handle
    _debug_handle = h


def clear_bridge_debug_handle() -> None:
    """Clear the debug handle and reset fault queue."""
    global _debug_handle, _fault_queue
    _debug_handle = None
    _fault_queue.clear()


def get_bridge_debug_handle() -> BridgeDebugHandle | None:
    """Get the current debug handle.

    Returns:
        The current BridgeDebugHandle, or None.
    """
    return _debug_handle


def inject_bridge_fault(
    method: BridgeFaultMethod | str,
    kind: BridgeFaultKind | str,
    status: int,
    error_type: str | None = None,
    count: int = 1,
) -> None:
    """Queue a fault for injection on the next call to the named API method.

    Args:
        method: API method name to fault.
        kind: 'fatal' or 'transient'.
        status: HTTP status code to return.
        error_type: Error type string (for fatal faults).
        count: Number of times to inject before clearing.
    """
    fault = BridgeFault(
        method=method,
        kind=kind,
        status=status,
        error_type=error_type,
        count=count,
    )
    _fault_queue.append(fault)
    _log_for_debugging(
        f"[bridge:debug] Queued fault: {method} {kind}/{status}"
        + (f"/{error_type}" if error_type else "")
        + f" ×{count}"
    )


# =============================================================================
# Fault Injection Wrapper
# =============================================================================


def _consume_fault(method: str) -> BridgeFault | None:
    """Find and consume a matching fault from the queue.

    Args:
        method: API method name to match.

    Returns:
        The matching BridgeFault if found, else None.
    """
    for i, fault in enumerate(_fault_queue):
        if fault.method == method:
            fault.count -= 1
            if fault.count <= 0:
                _fault_queue.pop(i)
            return fault
    return None


def _throw_fault(fault: BridgeFault, context: str) -> NoReturn:
    """Throw the appropriate error type for a fault.

    Args:
        fault: The fault to throw.
        context: Context string for the error message.

    Raises:
        BridgeFatalError: For fatal faults.
        Error: For transient faults.
    """
    from claude_code.bridge.api import BridgeFatalError

    _log_for_debugging(
        f"[bridge:debug] Injecting {fault.kind} fault into {context}: "
        f"status={fault.status} errorType={fault.error_type}"
    )
    if fault.kind == "fatal":
        raise BridgeFatalError(
            f"[injected] {context} {fault.status}",
            fault.status,
            fault.error_type,
        )
    # Transient: mimic an axios rejection (5xx / network)
    raise RuntimeError(f"[injected transient] {context} {fault.status}")


class BridgeApiClient:
    """Minimal interface that the fault-injection wrapper exposes."""

    async def poll_for_work(
        self,
        env_id: str,
        secret: str,
        signal: Any,
        reclaim_ms: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def register_bridge_environment(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def reconnect_session(
        self,
        env_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    async def heartbeat_work(
        self,
        env_id: str,
        work_id: str,
        token: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


def wrap_api_for_fault_injection(
    api: BridgeApiClient,
) -> BridgeApiClient:
    """Wrap a BridgeApiClient for fault injection.

    Each call first checks the fault queue. If a matching fault is queued,
    throws the specified error instead of calling through. Delegates
    everything else to the real client.

    Only called when USER_TYPE === 'ant' — zero overhead in external builds.

    Args:
        api: The real BridgeApiClient to wrap.

    Returns:
        A BridgeApiClient that may inject faults.
    """

    async def poll_for_work(
        env_id: str,
        secret: str,
        signal: Any,
        reclaim_ms: int,
    ) -> dict[str, Any]:
        f = _consume_fault("pollForWork")
        if f:
            _throw_fault(f, "Poll")
        return await api.poll_for_work(env_id, secret, signal, reclaim_ms)

    async def register_bridge_environment(
        config: dict[str, Any],
    ) -> dict[str, Any]:
        f = _consume_fault("registerBridgeEnvironment")
        if f:
            _throw_fault(f, "Registration")
        return await api.register_bridge_environment(config)

    async def reconnect_session(
        env_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        f = _consume_fault("reconnectSession")
        if f:
            _throw_fault(f, "ReconnectSession")
        return await api.reconnect_session(env_id, session_id)

    async def heartbeat_work(
        env_id: str,
        work_id: str,
        token: str,
    ) -> dict[str, Any]:
        f = _consume_fault("heartbeatWork")
        if f:
            _throw_fault(f, "Heartbeat")
        return await api.heartbeat_work(env_id, work_id, token)

    class WrappedApi(BridgeApiClient):
        __slots__ = ("_api",)

        def __init__(self, api: BridgeApiClient) -> None:
            self._api = api

        async def poll_for_work(
            self,
            env_id: str,
            secret: str,
            signal: Any,
            reclaim_ms: int,
        ) -> dict[str, Any]:
            f = _consume_fault("pollForWork")
            if f:
                _throw_fault(f, "Poll")
            return await self._api.poll_for_work(
                env_id, secret, signal, reclaim_ms
            )

        async def register_bridge_environment(
            self,
            config: dict[str, Any],
        ) -> dict[str, Any]:
            f = _consume_fault("registerBridgeEnvironment")
            if f:
                _throw_fault(f, "Registration")
            return await self._api.register_bridge_environment(config)

        async def reconnect_session(
            self,
            env_id: str,
            session_id: str,
        ) -> dict[str, Any]:
            f = _consume_fault("reconnectSession")
            if f:
                _throw_fault(f, "ReconnectSession")
            return await self._api.reconnect_session(env_id, session_id)

        async def heartbeat_work(
            self,
            env_id: str,
            work_id: str,
            token: str,
        ) -> dict[str, Any]:
            f = _consume_fault("heartbeatWork")
            if f:
                _throw_fault(f, "Heartbeat")
            return await self._api.heartbeat_work(env_id, work_id, token)

    return WrappedApi(api)
