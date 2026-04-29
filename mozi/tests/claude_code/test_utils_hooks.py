"""Tests for utils/hooks.py."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import pytest

from claude_code.utils.hooks import (
    HookCommand,
    HookEvent,
    HookResult,
    clear_hooks,
    create_base_hook_input,
    exec_command_hook,
    get_hooks_for_event,
    is_non_interactive,
    is_workspace_trusted,
    parse_hook_output,
    register_hook,
    run_hooks_for_event,
    should_skip_hook_due_to_trust,
    unregister_hook,
)


class TestHookEvent:
    """Tests for HookEvent enum."""

    def test_values(self) -> None:
        assert HookEvent.PRE_TOOL_USE.value == "PreToolUse"
        assert HookEvent.POST_TOOL_USE.value == "PostToolUse"
        assert HookEvent.SESSION_START.value == "SessionStart"
        assert HookEvent.SESSION_END.value == "SessionEnd"
        assert HookEvent.STOP.value == "Stop"


class TestHookCommand:
    """Tests for HookCommand dataclass."""

    def test_basic(self) -> None:
        cmd = HookCommand(command="echo hello")
        assert cmd.command == "echo hello"
        assert cmd.args == []
        assert cmd.timeout_ms == 30000

    def test_with_args(self) -> None:
        cmd = HookCommand(command="echo", args=["hello", "world"])
        assert cmd.command == "echo"
        assert cmd.args == ["hello", "world"]


class TestHookResult:
    """Tests for HookResult."""

    def test_default(self) -> None:
        result = HookResult()
        assert result.outcome == "success"
        assert result.message is None

    def test_from_dict(self) -> None:
        data = {
            "message": "hello",
            "outcome": "modified",
            "preventContinuation": True,
        }
        result = HookResult.from_dict(data)
        assert result.message == "hello"
        assert result.outcome == "modified"
        assert result.prevent_continuation is True

    def test_to_dict(self) -> None:
        result = HookResult(message="test", outcome="success")
        d = result.to_dict()
        assert d["message"] == "test"
        assert d["outcome"] == "success"


class TestCreateBaseHookInput:
    """Tests for create_base_hook_input."""

    def test_empty(self) -> None:
        inp = create_base_hook_input()
        assert inp["permissionMode"] is None
        assert inp["sessionId"] is None
        assert inp["agentInfo"] == {}

    def test_with_values(self) -> None:
        inp = create_base_hook_input(
            permission_mode="auto",
            session_id="sess_123",
            agent_info={"name": "claude"},
        )
        assert inp["permissionMode"] == "auto"
        assert inp["sessionId"] == "sess_123"
        assert inp["agentInfo"]["name"] == "claude"


class TestIsWorkspaceTrusted:
    """Tests for is_workspace_trusted."""

    def test_not_trusted(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            clear_hooks()
            assert is_workspace_trusted() is False

    def test_trusted(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_TRUSTED": "1"}):
            assert is_workspace_trusted() is True


class TestIsNonInteractive:
    """Tests for is_non_interactive."""

    def test_not_sdk(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert is_non_interactive() is False

    def test_sdk_mode(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_SDK": "1"}):
            assert is_non_interactive() is True


class TestShouldSkipHookDueToTrust:
    """Tests for should_skip_hook_due_to_trust."""

    def test_sdk_mode_never_skips(self) -> None:
        with patch.dict(os.environ, {"CLAUDE_SDK": "1"}):
            clear_hooks()
            assert should_skip_hook_due_to_trust() is False

    def test_untrusted_workspace_skips(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            clear_hooks()
            assert should_skip_hook_due_to_trust() is True


class TestParseHookOutput:
    """Tests for parse_hook_output."""

    def test_empty(self) -> None:
        result = parse_hook_output("")
        assert result["outcome"] == "success"

    def test_whitespace(self) -> None:
        result = parse_hook_output("   \n  ")
        assert result["outcome"] == "success"

    def test_valid_json(self) -> None:
        result = parse_hook_output('{"message": "hi", "outcome": "modified"}')
        assert result["message"] == "hi"
        assert result["outcome"] == "modified"

    def test_invalid_json(self) -> None:
        result = parse_hook_output("not json")
        assert result["outcome"] == "success"


class TestRegisterHook:
    """Tests for register_hook and related functions."""

    def test_register_and_get(self) -> None:
        clear_hooks()
        cmd = HookCommand(command="echo test")
        register_hook(HookEvent.SESSION_START, cmd)
        hooks = get_hooks_for_event(HookEvent.SESSION_START)
        assert len(hooks) == 1
        assert hooks[0].command == "echo test"

    def test_register_multiple(self) -> None:
        clear_hooks()
        cmd1 = HookCommand(command="echo 1")
        cmd2 = HookCommand(command="echo 2")
        register_hook(HookEvent.SESSION_START, cmd1)
        register_hook(HookEvent.SESSION_START, cmd2)
        hooks = get_hooks_for_event(HookEvent.SESSION_START)
        assert len(hooks) == 2

    def test_unregister(self) -> None:
        clear_hooks()
        cmd = HookCommand(command="echo test")
        register_hook(HookEvent.SESSION_START, cmd)
        unregister_hook(HookEvent.SESSION_START, cmd)
        hooks = get_hooks_for_event(HookEvent.SESSION_START)
        assert len(hooks) == 0

    def test_unregister_nonexistent(self) -> None:
        clear_hooks()
        cmd = HookCommand(command="echo test")
        unregister_hook(HookEvent.SESSION_START, cmd)

    def test_different_events(self) -> None:
        clear_hooks()
        cmd = HookCommand(command="echo")
        register_hook(HookEvent.SESSION_START, cmd)
        assert len(get_hooks_for_event(HookEvent.SESSION_END)) == 0


class TestClearHooks:
    """Tests for clear_hooks."""

    def test_clears_all(self) -> None:
        clear_hooks()
        cmd = HookCommand(command="echo")
        register_hook(HookEvent.SESSION_START, cmd)
        register_hook(HookEvent.SESSION_END, cmd)
        clear_hooks()
        assert len(get_hooks_for_event(HookEvent.SESSION_START)) == 0
        assert len(get_hooks_for_event(HookEvent.SESSION_END)) == 0


class TestRunHooksForEvent:
    """Tests for run_hooks_for_event."""

    async def test_skips_when_untrusted(self) -> None:
        clear_hooks()
        with patch.dict(os.environ, {}, clear=True):
            results = await run_hooks_for_event(
                HookEvent.SESSION_START, {"test": "data"}
            )
            assert results == []


class TestExecCommandHook:
    """Tests for exec_command_hook."""

    async def test_nonexistent_command(self) -> None:
        cmd = HookCommand(command="nonexistent_command_xyz_123")
        result = await exec_command_hook(
            cmd, HookEvent.SESSION_START, "test", "{}"
        )
        assert result["outcome"] == "error"
        assert "failed" in result["blockingError"]
