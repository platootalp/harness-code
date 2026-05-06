"""MCP configuration - backward compatibility shim.

This module is deprecated. Import from openharness.mcp_runtime instead.
"""

from openharness.mcp_runtime.config import load_mcp_server_configs

__all__ = ["load_mcp_server_configs"]