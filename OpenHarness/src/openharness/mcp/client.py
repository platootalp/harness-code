"""MCP client - backward compatibility shim.

This module is deprecated. Import from openharness.mcp_runtime instead.
"""

import httpx

from openharness.mcp_runtime.client import McpClientManager, McpServerNotConnectedError
from openharness.mcp_runtime.config import load_mcp_server_configs

__all__ = [
    "httpx",
    "McpClientManager",
    "McpServerNotConnectedError",
    "load_mcp_server_configs",
]