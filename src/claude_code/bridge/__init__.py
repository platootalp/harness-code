"""
Bridge module for Claude Code.

Provides messaging, transport, and protocol support for bridge connections.
"""

from claude_code.bridge.messaging import (
    BoundedUUIDSet,
    BridgeTransport,
    ServerControlRequestHandlers,
    handle_ingress_message,
    handle_server_control_request,
    is_eligible_bridge_message,
    is_sdk_control_request,
    is_sdk_control_response,
    is_sdk_message,
    make_result_message,
)
from claude_code.bridge.session import (
    BridgePointer,
    SessionInfo,
    SessionManager,
)
from claude_code.bridge.transport import (
    HybridTransport,
    SessionState,
    SSETransport,
    V1ReplTransport,
    V2ReplTransport,
    WebSocketTransport,
    create_v1_repl_transport,
    create_v2_repl_transport,
)

__all__ = [
    "BoundedUUIDSet",
    "BridgeTransport",
    "BridgePointer",
    "HybridTransport",
    "SSETransport",
    "ServerControlRequestHandlers",
    "SessionInfo",
    "SessionManager",
    "SessionState",
    "V1ReplTransport",
    "V2ReplTransport",
    "WebSocketTransport",
    "create_v1_repl_transport",
    "create_v2_repl_transport",
    "handle_ingress_message",
    "handle_server_control_request",
    "is_eligible_bridge_message",
    "is_sdk_control_request",
    "is_sdk_control_response",
    "is_sdk_message",
    "make_result_message",
]
