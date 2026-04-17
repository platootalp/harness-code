"""
Hook manager for executing plugin lifecycle hooks.

Manages registration and execution of hooks across all 25 event types.

TypeScript equivalent: src/utils/plugins/hooks.ts (loadPluginHooks)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .definitions import HookDefinition

logger = logging.getLogger(__name__)


class HookManager:
    """
    Manages plugin lifecycle hooks.

    Provides registration, filtering, and execution of hooks for all 25 event types.
    Hooks are sorted by priority (higher priority runs first).

    TypeScript equivalent: loadPluginHooks in utils/plugins/
    """

    def __init__(self) -> None:
        """Initialize the hook manager."""
        self._hooks: dict[str, list[HookDefinition]] = {}

    def register_hook(self, hook: HookDefinition) -> None:
        """Register a hook definition.

        Args:
            hook: The hook to register.
        """
        if hook.event not in self._hooks:
            self._hooks[hook.event] = []
        self._hooks[hook.event].append(hook)
        # Sort by priority (descending)
        self._hooks[hook.event].sort(key=lambda h: h.priority, reverse=True)
        logger.debug(f"Registered hook: {hook.event} (priority={hook.priority})")

    def unregister_hook(self, event: str) -> None:
        """Unregister all hooks for an event.

        Args:
            event: The hook event name.
        """
        self._hooks.pop(event, None)

    def get_hooks(self, event: str) -> list[HookDefinition]:
        """Get all hooks registered for an event.

        Args:
            event: The hook event name.

        Returns:
            List of hook definitions, sorted by priority.
        """
        return list(self._hooks.get(event, []))

    def list_registered_events(self) -> list[str]:
        """List all events with registered hooks.

        Returns:
            List of event names.
        """
        return [event for event, hooks in self._hooks.items() if hooks]

    def clear(self) -> None:
        """Remove all registered hooks."""
        self._hooks.clear()
        logger.debug("Cleared all hooks")

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def execute_pre_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Execute PreToolUse hooks.

        Returns (allowed, error_message). If any hook blocks, returns immediately.

        Args:
            tool_name: Name of the tool being called.
            tool_input: Input arguments to the tool.

        Returns:
            Tuple of (allowed, error_message).
        """
        context = {
            "tool": {"name": tool_name, "input": tool_input},
        }

        hooks = self.get_hooks("PreToolUse")
        for hook in hooks:
            if hook.condition:
                matches = hook.matches_condition(context)
                if matches is False:
                    continue

            result = await self._execute_hook(hook, context)
            if result and result.get("blocked"):
                return False, result.get("message")

        return True, None

    async def execute_post_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_result: str,
    ) -> None:
        """Execute PostToolUse hooks.

        Args:
            tool_name: Name of the tool that was called.
            tool_input: Input arguments to the tool.
            tool_result: Result string from the tool.
        """
        context = {
            "tool": {"name": tool_name, "input": tool_input, "result": tool_result},
        }

        hooks = self.get_hooks("PostToolUse")
        for hook in hooks:
            if hook.condition:
                matches = hook.matches_condition(context)
                if matches is False:
                    continue

            await self._execute_hook(hook, context)

    async def execute_post_tool_use_failure(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        error: str,
    ) -> None:
        """Execute PostToolUseFailure hooks.

        Args:
            tool_name: Name of the tool that failed.
            tool_input: Input arguments to the tool.
            error: Error message.
        """
        context = {
            "tool": {"name": tool_name, "input": tool_input},
            "error": error,
        }

        hooks = self.get_hooks("PostToolUseFailure")
        for hook in hooks:
            await self._execute_hook(hook, context)

    async def _execute_hook(
        self,
        hook: HookDefinition,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Execute a single hook.

        Args:
            hook: The hook definition.
            context: Context data passed to the hook.

        Returns:
            Hook result dict, or None.
        """
        try:
            result = await hook.execute(context)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error(f"Hook execution error in {hook.event}: {e}")
            return {"error": str(e)}
