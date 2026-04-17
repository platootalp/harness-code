"""Permission system."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from ..state.app_state import PermissionContext, PermissionRule, PermissionResult


def check_permission(
    tool_name: str,
    tool_input: dict,
    permission_context: PermissionContext,
) -> PermissionResult:
    """Check if a tool call is permitted based on rules."""
    # Check always_deny rules first (highest priority)
    for rule in permission_context.always_deny:
        if _matches_rule(rule, tool_name, tool_input):
            return PermissionResult(
                behavior='deny',
                reason=f"Denied by {rule.source} rule"
            )

    # Check always_allow rules
    for rule in permission_context.always_allow:
        if _matches_rule(rule, tool_name, tool_input):
            return PermissionResult(behavior='allow')

    # If mode is bypass, allow everything
    if permission_context.mode == 'bypass':
        return PermissionResult(behavior='allow')

    # Default: ask for permission
    return PermissionResult(behavior='ask')


def _matches_rule(rule: PermissionRule, tool_name: str, tool_input: dict) -> bool:
    """Check if a rule matches the tool call."""
    if rule.tool_name != tool_name and rule.tool_name != '*':
        return False

    # Check pattern match for command-based tools
    if rule.pattern and 'command' in tool_input:
        return fnmatch.fnmatch(tool_input['command'], rule.pattern)

    return True
