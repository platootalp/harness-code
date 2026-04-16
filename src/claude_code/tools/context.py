"""
Tool execution context types.

This module re-exports the ToolUseContext class and related types
from the models module for convenience. The canonical location for
these types is claude_code.models.tool.

Corresponds to TypeScript src/Tool.ts (ToolUseContext interface).
"""

from __future__ import annotations

from claude_code.models.tool import (
    CanUseToolFn,
    CompactProgressEvent,
    PermissionAllowResult,
    PermissionAskResult,
    PermissionDenyResult,
    PermissionPassthroughResult,
    PermissionResult,
    ToolCallProgress,
    ToolPermissionContext,
    ToolProgress,
    ToolUseContext,
    get_empty_tool_permission_context,
)

__all__ = [
    "CanUseToolFn",
    "CompactProgressEvent",
    "PermissionAskResult",
    "PermissionAllowResult",
    "PermissionDenyResult",
    "PermissionPassthroughResult",
    "PermissionResult",
    "ToolCallProgress",
    "ToolPermissionContext",
    "ToolProgress",
    "ToolUseContext",
    "get_empty_tool_permission_context",
]
