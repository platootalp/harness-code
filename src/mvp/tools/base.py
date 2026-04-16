"""Tool system base - build_tool factory."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..state.app_state import PermissionContext, PermissionRule, PermissionResult


@dataclass
class ToolResult:
    data: Any
    error: str | None = None


@dataclass
class ToolContext:
    cwd: str
    permission_context: PermissionContext


TOOL_DEFAULTS = {
    'is_enabled': lambda: True,
    'is_concurrency_safe': lambda _: False,
    'is_read_only': lambda _: False,
    'is_destructive': lambda _: False,
    'check_permissions': lambda _, __: PermissionResult(behavior='allow'),
    'to_auto_classifier_input': lambda _: '',
}


def build_tool(tool_def: dict) -> Any:
    """Factory function to create tools with defaults."""
    return {
        **TOOL_DEFAULTS,
        **tool_def,
    }


def check_permission_for_tool(
    tool_name: str,
    tool_input: Any,
    permission_context: PermissionContext,
) -> PermissionResult:
    """Check if a tool call is permitted based on rules."""
    # Check deny rules first
    for rule in permission_context.always_deny:
        if rule.tool_name == tool_name or rule.tool_name == '*':
            if rule.pattern is None:
                return PermissionResult(behavior='deny', reason=f"Tool {tool_name} is denied")
            # Pattern matching for bash commands
            if hasattr(tool_input, 'command') and rule.pattern:
                import fnmatch
                if fnmatch.fnmatch(tool_input.command, rule.pattern):
                    return PermissionResult(behavior='deny', reason=f"Command matches deny pattern {rule.pattern}")

    # Check allow rules
    for rule in permission_context.always_allow:
        if rule.tool_name == tool_name or rule.tool_name == '*':
            if rule.pattern is None:
                return PermissionResult(behavior='allow')
            if hasattr(tool_input, 'command') and rule.pattern:
                import fnmatch
                if fnmatch.fnmatch(tool_input.command, rule.pattern):
                    return PermissionResult(behavior='allow')

    return PermissionResult(behavior='ask')
