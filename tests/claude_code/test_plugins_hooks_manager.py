"""
Tests for plugins/hooks/manager.py - Hook execution manager.
"""

from __future__ import annotations

import pytest

from src.claude_code.plugins.hooks.definitions import HookDefinition, HookType


class TestHookManagerInit:
    """Tests for HookManager initialization."""

    def test_create_empty_manager(self) -> None:
        """Create a hook manager with no hooks."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        assert manager.list_registered_events() == []


class TestRegisterHook:
    """Tests for hook registration."""

    def test_register_hook(self) -> None:
        """Register a single hook."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        hook = HookDefinition(event="PreToolUse", hook_type=HookType.COMMAND, command="echo test")
        manager.register_hook(hook)
        assert "PreToolUse" in manager.list_registered_events()

    def test_register_multiple_same_event(self) -> None:
        """Register multiple hooks for the same event."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        hook1 = HookDefinition(event="SessionStart", priority=10)
        hook2 = HookDefinition(event="SessionStart", priority=5)
        manager.register_hook(hook1)
        manager.register_hook(hook2)
        hooks = manager.get_hooks("SessionStart")
        assert len(hooks) == 2

    def test_register_different_events(self) -> None:
        """Register hooks for different events."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        manager.register_hook(HookDefinition(event="PreToolUse"))
        manager.register_hook(HookDefinition(event="PostToolUse"))
        manager.register_hook(HookDefinition(event="SessionStart"))
        events = manager.list_registered_events()
        assert len(events) == 3

    def test_unregister_hook(self) -> None:
        """Unregister a specific hook."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        hook = HookDefinition(event="Setup", hook_type=HookType.COMMAND, command="echo setup")
        manager.register_hook(hook)
        manager.unregister_hook("Setup")
        assert manager.get_hooks("Setup") == []


class TestPreToolUse:
    """Tests for PreToolUse hook execution."""

    @pytest.mark.asyncio
    async def test_no_pre_tool_hooks(self) -> None:
        """When no PreToolUse hooks registered, returns allowed."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        allowed, msg = await manager.execute_pre_tool_use("Bash", {"command": "ls"})
        assert allowed is True
        assert msg is None

    @pytest.mark.asyncio
    async def test_pre_tool_hook_allows(self) -> None:
        """PreToolUse hook that allows passes through."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        manager.register_hook(
            HookDefinition(event="PreToolUse", hook_type=HookType.COMMAND, command="echo allowed")
        )
        allowed, msg = await manager.execute_pre_tool_use("Bash", {"command": "ls"})
        assert allowed is True

    @pytest.mark.asyncio
    async def test_pre_tool_hook_blocks(self) -> None:
        """PreToolUse hook can block a tool."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()

        async def blocking_hook(context: dict) -> dict:
            return {"blocked": True, "message": "Not allowed"}

        hook = HookDefinition(event="PreToolUse", hook_type=HookType.COMMAND, command="echo block")
        hook.execute = blocking_hook  # type: ignore
        manager.register_hook(hook)
        allowed, msg = await manager.execute_pre_tool_use("Bash", {"command": "ls"})
        assert allowed is False
        assert msg == "Not allowed"

    @pytest.mark.asyncio
    async def test_pre_tool_hook_with_condition_matches(self) -> None:
        """Hook with matching condition executes."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        called = []

        async def counting_hook(context: dict) -> dict:
            called.append(1)
            return {}

        hook = HookDefinition(
            event="PreToolUse",
            hook_type=HookType.COMMAND,
            command="echo test",
            condition="tool.name == 'Bash'",
        )
        hook.execute = counting_hook  # type: ignore
        manager.register_hook(hook)
        allowed, _ = await manager.execute_pre_tool_use("Bash", {"command": "ls"})
        assert allowed is True
        assert called == [1]

    @pytest.mark.asyncio
    async def test_pre_tool_hook_with_condition_not_matches(self) -> None:
        """Hook with non-matching condition does not execute."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        called = []

        async def counting_hook(context: dict) -> dict:
            called.append(1)
            return {}

        hook = HookDefinition(
            event="PreToolUse",
            hook_type=HookType.COMMAND,
            command="echo test",
            condition="tool.name == 'Read'",
        )
        hook._execute_hook = counting_hook  # type: ignore
        manager.register_hook(hook)
        allowed, _ = await manager.execute_pre_tool_use("Bash", {"command": "ls"})
        assert allowed is True
        assert called == []  # Hook was skipped due to condition


class TestPostToolUse:
    """Tests for PostToolUse hook execution."""

    @pytest.mark.asyncio
    async def test_no_post_tool_hooks(self) -> None:
        """When no PostToolUse hooks registered, returns immediately."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        await manager.execute_post_tool_use("Bash", {"command": "ls"}, "files listed")
        # No error means success

    @pytest.mark.asyncio
    async def test_post_tool_hook_called(self) -> None:
        """PostToolUse hook is called after tool execution."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        called = []

        async def post_hook(context: dict) -> None:
            called.append(context.get("tool", {}).get("result"))

        hook = HookDefinition(event="PostToolUse", hook_type=HookType.COMMAND, command="echo done")
        hook.execute = post_hook  # type: ignore
        manager.register_hook(hook)
        await manager.execute_post_tool_use("Bash", {"command": "ls"}, "result")
        assert called == ["result"]


class TestClearHooks:
    """Tests for clearing hooks."""

    def test_clear_all_hooks(self) -> None:
        """Clear removes all registered hooks."""
        from src.claude_code.plugins.hooks.manager import HookManager

        manager = HookManager()
        manager.register_hook(HookDefinition(event="PreToolUse"))
        manager.register_hook(HookDefinition(event="PostToolUse"))
        manager.clear()
        assert manager.list_registered_events() == []
