"""
Tests for hooks/manager.py - HookManager, HookEventEmitter, AsyncHookRegistry, SessionHookManager.
"""

from __future__ import annotations

import asyncio

import pytest
from claude_code.hooks.manager import (
    _HOOK_EVENT_METADATA,
    AsyncHookRegistry,
    FunctionHook,
    HookEvent,
    HookEventEmitter,
    HookInput,
    HookOutput,
    HookType,
    SessionHookEntry,
    SessionHookManager,
    SessionHookMatcher,
    SessionHookStore,
    _async_hook_registry,
    _hook_event_emitter,
    get_async_hook_registry,
    get_hook_event_emitter,
)


class TestHookEvent:
    """Tests for HookEvent enum."""

    def test_event_values(self) -> None:
        """Test hook event enum values."""
        assert HookEvent.PRE_TOOL_USE.value == "PreToolUse"
        assert HookEvent.POST_TOOL_USE.value == "PostToolUse"
        assert HookEvent.POST_TOOL_USE_FAILURE.value == "PostToolUseFailure"
        assert HookEvent.PERMISSION_DENIED.value == "PermissionDenied"

    def test_all_events_defined(self) -> None:
        """Test that all expected events are present."""
        expected_members = [
            "PRE_TOOL_USE",
            "POST_TOOL_USE",
            "POST_TOOL_USE_FAILURE",
            "PERMISSION_DENIED",
            "NOTIFICATION",
            "USER_PROMPT_SUBMIT",
            "SESSION_START",
            "SESSION_END",
            "STOP",
            "PERMISSION_REQUEST",
            "SETUP",
            "ELICITATION",
            "CONFIG_CHANGE",
        ]
        for name in expected_members:
            assert hasattr(HookEvent, name), f"Missing event: {name}"


class TestHookEventEmitter:
    """Tests for HookEventEmitter."""

    def test_global_instance(self) -> None:
        """Test that global instance is accessible."""
        emitter = get_hook_event_emitter()
        assert emitter is _hook_event_emitter

    def test_emit_started(self) -> None:
        """Test emitting hook started events."""
        emitter = HookEventEmitter()
        received: list[object] = []

        emitter.set_handler(lambda e: received.append(e))
        emitter.set_all_events_enabled(True)
        emitter.emit_started("hook-1", "my-hook", "PreToolUse")

        assert len(received) == 1
        assert received[0].type == "started"
        assert received[0].hook_id == "hook-1"

    def test_emit_progress(self) -> None:
        """Test emitting hook progress events."""
        emitter = HookEventEmitter()
        received: list[object] = []

        emitter.set_handler(lambda e: received.append(e))
        emitter.set_all_events_enabled(True)
        emitter.emit_progress("hook-1", "my-hook", "PreToolUse", "out", "err", "result")

        assert len(received) == 1
        assert received[0].type == "progress"
        assert received[0].stdout == "out"

    def test_emit_response(self) -> None:
        """Test emitting hook response events."""
        emitter = HookEventEmitter()
        received: list[object] = []

        emitter.set_handler(lambda e: received.append(e))
        emitter.set_all_events_enabled(True)
        emitter.emit_response("hook-1", "my-hook", "PreToolUse", "output", "out", "err", 0, "success")

        assert len(received) == 1
        assert received[0].type == "response"
        assert received[0].output == "output"
        assert received[0].exit_code == 0

    def test_event_filtering(self) -> None:
        """Test that events are properly filtered."""
        emitter = HookEventEmitter()
        received: list[object] = []

        emitter.set_handler(lambda e: received.append(e))
        # Default: only ALWAYS_EMITTED_EVENTS are sent
        emitter.emit_started("hook-1", "hook", "PreToolUse")  # Not in always-emitted
        assert len(received) == 0

        # Enable all events
        emitter.set_all_events_enabled(True)
        emitter.emit_started("hook-2", "hook", "PreToolUse")
        assert len(received) == 1

    def test_pending_events_queue(self) -> None:
        """Test that events are queued when no handler is set."""
        emitter = HookEventEmitter()
        emitter.set_all_events_enabled(True)
        emitter.emit_started("hook-1", "my-hook", "PreToolUse")
        emitter.emit_started("hook-2", "my-hook", "PreToolUse")

        # Access private _pending_events attribute
        pending = emitter._pending_events  # type: ignore[attr-defined]
        assert len(pending) == 2
        assert pending[0].hook_id == "hook-1"
        assert pending[1].hook_id == "hook-2"

    def test_clear(self) -> None:
        """Test clearing emitter state."""
        emitter = HookEventEmitter()
        emitter.set_all_events_enabled(True)
        emitter.emit_started("hook-1", "my-hook", "PreToolUse")

        emitter.clear()
        assert emitter._pending_events == []  # type: ignore[attr-defined]
        assert emitter._all_events_enabled is False


class TestAsyncHookRegistry:
    """Tests for AsyncHookRegistry."""

    def test_register_and_get(self) -> None:
        """Test registering and retrieving pending hooks."""
        registry = AsyncHookRegistry()
        registry.register("proc-1", "hook-1", "hook-name", "PreToolUse", "echo test")

        hook = registry.get("proc-1")
        assert hook is not None
        assert hook.process_id == "proc-1"
        assert hook.hook_id == "hook-1"
        assert hook.command == "echo test"

    def test_get_all(self) -> None:
        """Test getting all pending hooks."""
        registry = AsyncHookRegistry()
        registry.register("proc-1", "hook-1", "hook-name", "PreToolUse", "echo test")
        registry.register("proc-2", "hook-2", "hook-name", "PostToolUse", "echo test2")

        all_hooks = registry.get_all()
        assert len(all_hooks) == 2

    def test_get_active(self) -> None:
        """Test getting active (non-attached) hooks."""
        registry = AsyncHookRegistry()
        registry.register("proc-1", "hook-1", "hook-name", "PreToolUse", "echo test")
        registry.register("proc-2", "hook-2", "hook-name", "PreToolUse", "echo test")
        registry.mark_attached("proc-1")

        active = registry.get_active()
        assert len(active) == 1
        assert active[0].process_id == "proc-2"

    def test_remove(self) -> None:
        """Test removing a pending hook."""
        registry = AsyncHookRegistry()
        registry.register("proc-1", "hook-1", "hook-name", "PreToolUse", "echo test")

        registry.remove("proc-1")
        assert registry.get("proc-1") is None
        assert len(registry) == 0

    def test_check_timeout(self) -> None:
        """Test timeout detection."""
        registry = AsyncHookRegistry()
        # Register with 0 timeout - should be immediately timed out
        registry.register("proc-1", "hook-1", "hook-name", "PreToolUse", "sleep 10", timeout=0.0)

        timed_out = registry.check_timeout()
        assert "proc-1" in timed_out

    def test_global_registry(self) -> None:
        """Test global registry access."""
        registry = get_async_hook_registry()
        assert registry is _async_hook_registry


class TestSessionHookManager:
    """Tests for SessionHookManager."""

    def test_add_command_hook(self) -> None:
        """Test adding a command hook."""
        manager = SessionHookManager()
        manager.add_command_hook(
            "session-1",
            HookEvent.PRE_TOOL_USE,
            "ToolName",
            "echo test",
        )

        matchers = manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 1
        assert matchers[0].matcher == "ToolName"
        assert len(matchers[0].hooks) == 1

    def test_add_command_hook_same_matcher(self) -> None:
        """Test adding multiple command hooks with same matcher."""
        manager = SessionHookManager()
        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "ToolName", "echo first")
        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "ToolName", "echo second")

        matchers = manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 1  # Same matcher, one group
        assert len(matchers[0].hooks) == 2  # Two hooks in that group

    def test_add_function_hook(self) -> None:
        """Test adding a function hook."""
        manager = SessionHookManager()

        async def my_callback() -> bool:
            return True

        hook_id = manager.add_function_hook(
            "session-1",
            HookEvent.PRE_TOOL_USE,
            "ToolName",
            my_callback,
        )
        assert hook_id.startswith("fn-hook-")

    def test_add_function_hook_returns_id(self) -> None:
        """Test that add_function_hook returns consistent IDs."""
        manager = SessionHookManager()

        def cb() -> bool:
            return True

        id1 = manager.add_function_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", cb)
        id2 = manager.add_function_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", cb)
        assert id1 != id2

    def test_get_function_hooks_for_event(self) -> None:
        """Test retrieving function hooks for an event."""
        manager = SessionHookManager()

        def cb1() -> bool:
            return True

        def cb2() -> bool:
            return False

        manager.add_function_hook("session-1", HookEvent.PRE_TOOL_USE, "ToolName", cb1)
        manager.add_function_hook("session-1", HookEvent.PRE_TOOL_USE, "ToolName", cb2)
        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "ToolName", "echo cmd")

        fn_hooks = manager.get_function_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        assert len(fn_hooks) == 2  # Only function hooks
        assert all(isinstance(h, FunctionHook) for _, h in fn_hooks)

    def test_get_hooks_for_event_empty_session(self) -> None:
        """Test getting hooks for unknown session."""
        manager = SessionHookManager()
        hooks = manager.get_hooks_for_event("unknown-session", HookEvent.PRE_TOOL_USE)
        assert hooks == []

    def test_get_hooks_for_event_empty_event(self) -> None:
        """Test getting hooks for event with no hooks."""
        manager = SessionHookManager()
        hooks = manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        assert hooks == []

    def test_remove_function_hook(self) -> None:
        """Test removing a function hook."""
        manager = SessionHookManager()

        def cb() -> bool:
            return True

        hook_id = manager.add_function_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", cb)
        removed = manager.remove_function_hook("session-1", HookEvent.PRE_TOOL_USE, hook_id)
        assert removed is True

        # Should be gone now
        fn_hooks = manager.get_function_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        assert fn_hooks == []

    def test_remove_function_hook_not_found(self) -> None:
        """Test removing non-existent function hook."""
        manager = SessionHookManager()
        removed = manager.remove_function_hook("session-1", HookEvent.PRE_TOOL_USE, "non-existent")
        assert removed is False

    def test_clear_session(self) -> None:
        """Test clearing all hooks for a session."""
        manager = SessionHookManager()
        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "ToolName", "echo test")
        manager.add_command_hook("session-1", HookEvent.POST_TOOL_USE, "Always", "echo post")

        manager.clear_session("session-1")

        assert manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE) == []
        assert manager.get_hooks_for_event("session-1", HookEvent.POST_TOOL_USE) == []

    def test_add_session_and_remove_session(self) -> None:
        """Test session lifecycle."""
        manager = SessionHookManager()
        assert len(manager) == 0

        manager.add_session("session-1")
        assert len(manager) == 1

        manager.remove_session("session-1")
        assert len(manager) == 0


class TestHookType:
    """Tests for HookType enum."""

    def test_values(self) -> None:
        """Test HookType values."""
        assert HookType.COMMAND.value == "command"
        assert HookType.PROMPT.value == "prompt"
        assert HookType.FUNCTION.value == "function"


class TestHookInput:
    """Tests for HookInput dataclass."""

    def test_create(self) -> None:
        """Test creating HookInput."""
        inp = HookInput(
            tool_name="bash",
            tool_input={"command": "ls"},
            tool_use_id="use-123",
        )
        assert inp.tool_name == "bash"
        assert inp.tool_input == {"command": "ls"}

    def test_to_json(self) -> None:
        """Test converting HookInput to JSON with camelCase."""
        inp = HookInput(tool_name="bash", tool_input={"cmd": "ls"}, tool_use_id="use-1")
        json_str = inp.to_json()
        assert '"toolName": "bash"' in json_str
        assert '"toolInput":' in json_str
        assert '"toolUseId": "use-1"' in json_str
        # Snake_case fields not present when None
        assert '"error"' not in json_str

    def test_to_json_extra_fields(self) -> None:
        """Test that extra fields are included in JSON."""
        inp = HookInput(tool_name="bash")
        inp.extra["customField"] = "value"
        json_str = inp.to_json()
        assert '"customField": "value"' in json_str


class TestHookOutput:
    """Tests for HookOutput dataclass."""

    def test_create(self) -> None:
        """Test creating HookOutput."""
        out = HookOutput(stdout="output", stderr="errors", exit_code=0)
        assert out.stdout == "output"
        assert out.exit_code == 0

    def test_with_json_output(self) -> None:
        """Test HookOutput with JSON response."""
        out = HookOutput(
            stdout="",
            stderr="",
            exit_code=0,
            json_output={"hookSpecificOutput": {"retry": True}},
        )
        assert out.json_output["hookSpecificOutput"]["retry"] is True


class TestHookEventMetadata:
    """Tests for _HOOK_EVENT_METADATA registry."""

    def test_metadata_exists(self) -> None:
        """Test that metadata registry is populated."""
        assert len(_HOOK_EVENT_METADATA) > 0

    def test_pre_tool_use_metadata(self) -> None:
        """Test PreToolUse metadata."""
        meta = _HOOK_EVENT_METADATA.get(HookEvent.PRE_TOOL_USE)
        assert meta is not None
        assert "Before tool execution" in meta.summary
        assert "Exit code" in meta.description
        assert meta.matcher_metadata is not None
        assert meta.matcher_metadata.field_to_match == "tool_name"

    def test_metadata_has_summary_and_description(self) -> None:
        """Test that all metadata entries have summary and description."""
        for event, meta in _HOOK_EVENT_METADATA.items():
            assert meta.summary, f"Missing summary for {event}"
            assert meta.description, f"Missing description for {event}"

    def test_core_events_in_metadata(self) -> None:
        """Test that core events have metadata."""
        for event in [HookEvent.PRE_TOOL_USE, HookEvent.POST_TOOL_USE, HookEvent.SESSION_START]:
            assert event in _HOOK_EVENT_METADATA, f"Missing metadata for {event}"


class TestSessionHookStore:
    """Tests for SessionHookStore."""

    def test_create(self) -> None:
        """Test creating a session hook store."""
        store = SessionHookStore()
        assert store.hooks == {}


class TestSessionHookMatcher:
    """Tests for SessionHookMatcher."""

    def test_create(self) -> None:
        """Test creating a session hook matcher."""
        matcher = SessionHookMatcher(matcher="ToolName", skill_root="/path/to/skills")
        assert matcher.matcher == "ToolName"
        assert matcher.skill_root == "/path/to/skills"
        assert matcher.hooks == []


class TestSessionHookEntry:
    """Tests for SessionHookEntry."""

    def test_create_with_command(self) -> None:
        """Test creating entry with command hook."""
        from claude_code.hooks.manager import HookCommand

        entry = SessionHookEntry(hook=HookCommand(command="echo test", prompt="Test prompt"))
        assert isinstance(entry.hook, HookCommand)
        assert entry.hook.command == "echo test"
        assert entry.hook.prompt == "Test prompt"

    def test_create_with_function(self) -> None:
        """Test creating entry with function hook."""
        entry = SessionHookEntry(hook=FunctionHook(id="fn-1", callback=lambda: True))
        assert isinstance(entry.hook, FunctionHook)
        assert entry.hook.id == "fn-1"

    def test_with_on_success_callback(self) -> None:
        """Test entry with on_success callback."""
        called: list[bool] = []

        def on_success(output: HookOutput) -> None:
            called.append(True)

        entry = SessionHookEntry(
            hook=FunctionHook(id="fn-1", callback=lambda: True),
            on_success=on_success,
        )
        entry.on_success(HookOutput(stdout="", stderr="", exit_code=0))
        assert called == [True]


class TestFunctionHook:
    """Tests for FunctionHook dataclass."""

    def test_create(self) -> None:
        """Test creating FunctionHook."""
        def my_callback() -> bool:
            return True

        hook = FunctionHook(
            id="fn-1",
            callback=my_callback,
            timeout=10.0,
            error_message="Failed",
            status_message="Running",
        )
        assert hook.id == "fn-1"
        assert hook.timeout == 10.0
        assert hook.error_message == "Failed"
        assert hook.status_message == "Running"


class TestSessionHookManagerIntegration:
    """Integration tests for SessionHookManager."""

    def test_multiple_sessions_independent(self) -> None:
        """Test that multiple sessions have independent hook state."""
        manager = SessionHookManager()

        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", "echo session1")
        manager.add_command_hook("session-2", HookEvent.PRE_TOOL_USE, "Always", "echo session2")

        sess1_hooks = manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        sess2_hooks = manager.get_hooks_for_event("session-2", HookEvent.PRE_TOOL_USE)

        assert len(sess1_hooks) == 1
        assert len(sess2_hooks) == 1
        assert sess1_hooks[0].hooks[0].hook.command == "echo session1"
        assert sess2_hooks[0].hooks[0].hook.command == "echo session2"

    def test_different_events_independent(self) -> None:
        """Test that different events have independent hooks."""
        manager = SessionHookManager()
        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", "echo pre")
        manager.add_command_hook("session-1", HookEvent.POST_TOOL_USE, "Always", "echo post")

        pre_hooks = manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        post_hooks = manager.get_hooks_for_event("session-1", HookEvent.POST_TOOL_USE)

        assert len(pre_hooks) == 1
        assert len(post_hooks) == 1
        assert pre_hooks[0].hooks[0].hook.command == "echo pre"
        assert post_hooks[0].hooks[0].hook.command == "echo post"

    def test_mixed_command_and_function_hooks(self) -> None:
        """Test mixing command and function hooks for same event."""
        manager = SessionHookManager()

        def my_callback() -> bool:
            return True

        manager.add_command_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", "echo cmd")
        manager.add_function_hook("session-1", HookEvent.PRE_TOOL_USE, "Always", my_callback)

        matchers = manager.get_hooks_for_event("session-1", HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 1
        assert len(matchers[0].hooks) == 2
