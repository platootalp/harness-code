"""
Base tool classes and tool definition utilities.

This module re-exports the BaseTool class and tool builder utilities
from the models module for convenience. The canonical location for
these types is claude_code.models.tool.

Corresponds to TypeScript src/Tool.ts (buildTool, ToolDef, BaseTool interface).
"""

from __future__ import annotations

from claude_code.models.tool import (
    TOOL_DEFAULTS,
    AnyObject,
    BaseTool,
    ToolDef,
    ToolInputJSONSchema,
    ValidationResult,
    build_tool,
)

__all__ = [
    "AnyObject",
    "BaseTool",
    "TOOL_DEFAULTS",
    "ToolDef",
    "ToolInputJSONSchema",
    "ValidationResult",
    "build_tool",
]
