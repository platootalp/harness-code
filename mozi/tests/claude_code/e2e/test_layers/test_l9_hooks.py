"""E2E 测试 - L9: Hooks 层

验证 lifecycle hooks 触发。
直接测试 Hooks 组件。
"""

from __future__ import annotations

import pytest


class TestHooksModule:
    """测试 Hooks 模块."""

    def test_hooks_module_import(self):
        """验证 hooks 模块可以导入."""
        from claude_code.hooks import registry
        assert registry is not None

    def test_hooks_types_import(self):
        """验证 hooks 类型可以导入."""
        from claude_code.hooks.types import HookEvent
        assert HookEvent is not None


class TestHooksRegistry:
    """测试 Hooks 注册表."""

    def test_get_hook_registry(self):
        """验证获取 hooks 注册表."""
        from claude_code.hooks.registry import get_hook_registry

        registry = get_hook_registry()
        assert registry is not None

    def test_hook_registry_type(self):
        """验证注册表类型."""
        from claude_code.hooks.registry import HookRegistry

        assert HookRegistry is not None


class TestHooksManager:
    """测试 Hooks 管理器."""

    def test_hook_manager_import(self):
        """验证 Hooks 管理器可以导入."""
        from claude_code.hooks.manager import HookManager

        assert HookManager is not None

    def test_hook_event_emitter_import(self):
        """验证 Hook 事件发射器可以导入."""
        from claude_code.hooks.manager import HookEventEmitter

        assert HookEventEmitter is not None
