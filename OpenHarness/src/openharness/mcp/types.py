"""MCP types - backward compatibility shim.

This module is deprecated. Import from openharness.mcp_runtime instead.
"""

from openharness.mcp_runtime.types import (
    McpConnectionStatus,
    McpHttpServerConfig,
    McpJsonConfig,
    McpResourceInfo,
    McpServerConfig,
    McpStdioServerConfig,
    McpToolInfo,
    McpWebSocketServerConfig,
)

__all__ = [
    "McpConnectionStatus",
    "McpHttpServerConfig",
    "McpJsonConfig",
    "McpResourceInfo",
    "McpServerConfig",
    "McpStdioServerConfig",
    "McpToolInfo",
    "McpWebSocketServerConfig",
]