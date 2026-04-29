"""
Tests for tools/context.py - ToolUseContext and permission types.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from claude_code.models.tool import (
    PermissionAllowResult,
    PermissionAskResult,
    PermissionDenyResult,
    ToolPermissionContext,
    ToolUseContext,
    get_empty_tool_permission_context,
)


class TestToolPermissionContext:
    """Tests for ToolPermissionContext."""

    def test_default_context(self) -> None:
        ctx = ToolPermissionContext()
        assert ctx.mode == "default"
        assert ctx.additional_working_directories == {}
        assert ctx.always_allow_rules == {}
        assert ctx.always_deny_rules == {}
        assert ctx.always_ask_rules == {}
        assert ctx.is_bypass_permissions_mode_available is False

    def test_custom_context(self) -> None:
        ctx = ToolPermissionContext(
            mode="bypass",
            is_bypass_permissions_mode_available=True,
        )
        assert ctx.mode == "bypass"
        assert ctx.is_bypass_permissions_mode_available is True

    def test_frozen_immutability(self) -> None:
        ctx = ToolPermissionContext()
        with pytest.raises(AttributeError):
            ctx.mode = "changed"  # type: ignore[attr-defined]

    def test_get_empty_tool_permission_context(self) -> None:
        ctx = get_empty_tool_permission_context()
        assert isinstance(ctx, ToolPermissionContext)
        assert ctx.mode == "default"


class TestToolUseContext:
    """Tests for ToolUseContext."""

    @pytest.fixture
    def loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.new_event_loop()

    @pytest.fixture
    def context(self, loop: asyncio.AbstractEventLoop) -> ToolUseContext:
        return ToolUseContext(abort_controller=loop)

    def test_basic_context_creation(self, context: ToolUseContext) -> None:
        assert context.abort_controller is not None
        assert context.debug is False
        assert context.verbose is False
        assert context.commands == []
        assert context.messages == []

    def test_context_with_values(
        self, loop: asyncio.AbstractEventLoop
    ) -> None:
        ctx = ToolUseContext(
            abort_controller=loop,
            debug=True,
            verbose=True,
            main_loop_model="claude-3-5",
            max_budget_usd=10.0,
        )
        assert ctx.debug is True
        assert ctx.verbose is True
        assert ctx.main_loop_model == "claude-3-5"
        assert ctx.max_budget_usd == 10.0

    def test_context_nested_tracking(self, context: ToolUseContext) -> None:
        assert context.nested_memory_attachment_triggers == set()

    def test_context_with_tool_permission_context(
        self, loop: asyncio.AbstractEventLoop
    ) -> None:
        perm_ctx = ToolPermissionContext(mode="bypass")
        ctx = ToolUseContext(
            abort_controller=loop,
            tool_permission_context=perm_ctx,
        )
        assert ctx.tool_permission_context.mode == "bypass"

    def test_context_glob_limits(self, loop: asyncio.AbstractEventLoop) -> None:
        ctx = ToolUseContext(
            abort_controller=loop,
            glob_limits={"max_results": 100},
        )
        assert ctx.glob_limits == {"max_results": 100}

    def test_context_file_reading_limits(
        self, loop: asyncio.AbstractEventLoop
    ) -> None:
        ctx = ToolUseContext(
            abort_controller=loop,
            file_reading_limits={"max_tokens": 5000},
        )
        assert ctx.file_reading_limits == {"max_tokens": 5000}


class TestPermissionResults:
    """Tests for permission result types."""

    def test_permission_allow_result_default(self) -> None:
        result = PermissionAllowResult()
        assert result.behavior == "allow"
        assert result.updated_input is None
        assert result.user_modified is None

    def test_permission_allow_result_with_input(self) -> None:
        result = PermissionAllowResult(updated_input={"command": "ls"})
        assert result.behavior == "allow"
        assert result.updated_input == {"command": "ls"}

    def test_permission_ask_result_default(self) -> None:
        result = PermissionAskResult()
        assert result.behavior == "ask"
        assert result.message == ""

    def test_permission_ask_result_with_message(self) -> None:
        result = PermissionAskResult(
            message="Run git commit?",
            suggestions=["Yes", "No"],
        )
        assert result.behavior == "ask"
        assert result.message == "Run git commit?"
        assert result.suggestions == ["Yes", "No"]

    def test_permission_deny_result_default(self) -> None:
        result = PermissionDenyResult()
        assert result.behavior == "deny"
        assert result.message == ""

    def test_permission_deny_result_with_message(self) -> None:
        result = PermissionDenyResult(message="Permission denied")
        assert result.behavior == "deny"
        assert result.message == "Permission denied"
