"""MCP module - backward compatibility shim.

This module is deprecated. Import from openharness.mcp_runtime instead.
"""

from openharness.mcp_runtime import client, config, types

__all__ = ["client", "config", "types"]