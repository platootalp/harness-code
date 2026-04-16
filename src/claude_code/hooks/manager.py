"""
Hook system manager for Claude Code.

This module provides the core hook infrastructure including:
- Hook event types and metadata
- Hook execution event broadcasting
- Async hook registry for pending hook processes
- Session-scoped ephemeral hook management

Migrated from src/utils/hooks/ (TypeScript).

Architecture:
- Hook events are triggered at specific points in the Claude Code lifecycle
  (PreToolUse, PostToolUse, SessionStart, etc.)
- Hooks can be command-based (shell commands) or function-based (Python callbacks)
- Command hooks may be synchronous (blocking) or asynchronous (background process)
- Session hooks are ephemeral, in-memory only, cleared when session ends

Example:
    manager = HookManager()

    # Register a command hook
    manager.register_command_hook(
        event=HookEvent.PRE_TOOL_USE,
        matcher="bash",
        command="echo 'running bash'",
    )

    # Execute hooks for an event
    results = await manager.execute_hooks(
        event=HookEvent.PRE_TOOL_USE,
        input={"tool_name": "bash", "tool_input": {"command": "ls"}},
        tool_use_id="use-123",
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable

logger = logging.getLogger(__name__)


# =============================================================================
# Hook Event Types
# =============================================================================


class HookEvent(StrEnum):
    """All supported hook event types, matching TypeScript HookEvent."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    PERMISSION_DENIED = "PermissionDenied"
    NOTIFICATION = "Notification"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    PRE_COMPACT = "PreCompact"
    POST_COMPACT = "PostCompact"
    PERMISSION_REQUEST = "PermissionRequest"
    SETUP = "Setup"
    TEAMMATE_IDLE = "TeammateIdle"
    TASK_CREATED = "TaskCreated"
    TASK_COMPLETED = "TaskCompleted"
    ELICITATION = "Elicitation"
    ELICITATION_RESULT = "ElicitationResult"
    CONFIG_CHANGE = "ConfigChange"
    INSTRUCTIONS_LOADED = "InstructionsLoaded"
    WORKTREE_CREATE = "WorktreeCreate"
    WORKTREE_REMOVE = "WorktreeRemove"
    CWD_CHANGED = "CwdChanged"
    FILE_CHANGED = "FileChanged"


# Events that are always emitted regardless of includeHookEvents setting
ALWAYS_EMITTED_EVENTS: frozenset[str] = frozenset({
    HookEvent.SESSION_START.value,
    HookEvent.SETUP.value,
})

# All hook events
ALL_HOOK_EVENTS: list[str] = [e.value for e in HookEvent]


# =============================================================================
# Hook Configuration Types
# =============================================================================


class HookType(StrEnum):
    """Hook execution type."""

    COMMAND = "command"
    PROMPT = "prompt"
    FUNCTION = "function"


@dataclass
class HookCommand:
    """A command-based hook configuration."""

    command: str
    prompt: str | None = None


@dataclass
class HookConfig:
    """Complete hook configuration."""

    type: HookType
    command: str | None = None
    prompt: str | None = None
    timeout: int | None = None
    internal: bool = False


@dataclass
class MatcherMetadata:
    """Metadata for hook matcher fields."""

    field_to_match: str
    values: list[str]


@dataclass
class HookEventMetadata:
    """Metadata and description for a hook event type."""

    summary: str
    description: str
    matcher_metadata: MatcherMetadata | None = None


# =============================================================================
# Hook Input/Output Types
# =============================================================================


@dataclass
class HookInput:
    """Input passed to a hook command (as JSON on stdin)."""

    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    response: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None
    is_interrupt: bool = False
    is_timeout: bool = False
    reason: str | None = None
    notification_type: str | None = None
    notification_message: str | None = None
    session_start_source: str | None = None
    session_end_reason: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    agent_transcript_path: str | None = None
    compaction_trigger: str | None = None
    compaction_summary: str | None = None
    permission_mode: str | None = None
    setup_trigger: str | None = None
    teammate_name: str | None = None
    team_name: str | None = None
    task_id: str | None = None
    task_subject: str | None = None
    task_description: str | None = None
    mcp_server_name: str | None = None
    elicitation_message: str | None = None
    requested_schema: dict[str, Any] | None = None
    elicitation_id: str | None = None
    elicitation_action: str | None = None
    elicitation_content: str | None = None
    config_source: str | None = None
    file_path: str | None = None
    instruction_file_path: str | None = None
    memory_type: str | None = None
    load_reason: str | None = None
    worktree_name: str | None = None
    worktree_path: str | None = None
    old_cwd: str | None = None
    new_cwd: str | None = None
    file_event: str | None = None
    # Generic additional fields
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize hook input to JSON string for stdin."""
        data = {}
        for key, value in self.__dict__.items():
            if key == "extra":
                data.update(value)
            elif value is not None:
                # Convert snake_case to camelCase for TypeScript compat
                camel_key = _snake_to_camel(key)
                data[camel_key] = value
        return json.dumps(data, ensure_ascii=False)


def _snake_to_camel(snake: str) -> str:
    """Convert snake_case to camelCase."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


@dataclass
class HookOutput:
    """Output from a hook command."""

    stdout: str
    stderr: str
    exit_code: int
    json_output: dict[str, Any] | None = None


# =============================================================================
# Hook Execution Events (for broadcasting)
# =============================================================================


@dataclass
class HookStartedEvent:
    """Event emitted when a hook starts executing."""

    type: str = "started"
    hook_id: str = ""
    hook_name: str = ""
    hook_event: str = ""


@dataclass
class HookProgressEvent:
    """Event emitted during hook execution with progress output."""

    type: str = "progress"
    hook_id: str = ""
    hook_name: str = ""
    hook_event: str = ""
    stdout: str = ""
    stderr: str = ""
    output: str = ""


@dataclass
class HookResponseEvent:
    """Event emitted when a hook completes."""

    type: str = "response"
    hook_id: str = ""
    hook_name: str = ""
    hook_event: str = ""
    output: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    outcome: str = "success"  # "success" | "error" | "cancelled"


HookExecutionEvent = HookStartedEvent | HookProgressEvent | HookResponseEvent
HookEventHandler = Callable[[HookExecutionEvent], None]


# =============================================================================
# Hook Event Emitter
# =============================================================================


class HookEventEmitter:
    """Singleton event emitter for hook execution events."""

    def __init__(self) -> None:
        self._handler: HookEventHandler | None = None
        self._pending_events: list[HookExecutionEvent] = []
        self._all_events_enabled: bool = False

    def set_handler(self, handler: HookEventHandler | None) -> None:
        """Register a handler for hook execution events."""
        self._handler = handler
        if handler and self._pending_events:
            for event in self._pending_events:
                handler(event)
            self._pending_events.clear()

    def _should_emit(self, hook_event: str) -> bool:
        """Check if an event should be emitted based on settings."""
        if hook_event in ALWAYS_EMITTED_EVENTS:
            return True
        return self._all_events_enabled and hook_event in ALL_HOOK_EVENTS

    def _emit(self, event: HookExecutionEvent) -> None:
        """Emit an event to the handler or queue it."""
        if self._handler:
            self._handler(event)
        else:
            self._pending_events.append(event)
            if len(self._pending_events) > 100:
                self._pending_events.pop(0)

    def emit_started(
        self,
        hook_id: str,
        hook_name: str,
        hook_event: str,
    ) -> None:
        """Emit a HookStartedEvent."""
        if not self._should_emit(hook_event):
            return
        self._emit(HookStartedEvent(
            type="started",
            hook_id=hook_id,
            hook_name=hook_name,
            hook_event=hook_event,
        ))

    def emit_progress(
        self,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        stdout: str,
        stderr: str,
        output: str,
    ) -> None:
        """Emit a HookProgressEvent."""
        if not self._should_emit(hook_event):
            return
        self._emit(HookProgressEvent(
            type="progress",
            hook_id=hook_id,
            hook_name=hook_name,
            hook_event=hook_event,
            stdout=stdout,
            stderr=stderr,
            output=output,
        ))

    def emit_response(
        self,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        output: str,
        stdout: str,
        stderr: str,
        exit_code: int | None = None,
        outcome: str = "success",
    ) -> None:
        """Emit a HookResponseEvent."""
        if output or stderr:
            logger.debug(
                f"Hook {hook_name} ({hook_event}) {outcome}: "
                f"{output or stderr[:200]}"
            )
        if not self._should_emit(hook_event):
            return
        self._emit(HookResponseEvent(
            type="response",
            hook_id=hook_id,
            hook_name=hook_name,
            hook_event=hook_event,
            output=output,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            outcome=outcome,
        ))

    def set_all_events_enabled(self, enabled: bool) -> None:
        """Enable emission of all hook event types."""
        self._all_events_enabled = enabled

    def clear(self) -> None:
        """Clear all state."""
        self._handler = None
        self._pending_events.clear()
        self._all_events_enabled = False


# Global event emitter instance
_hook_event_emitter = HookEventEmitter()


def get_hook_event_emitter() -> HookEventEmitter:
    """Get the global HookEventEmitter instance."""
    return _hook_event_emitter


# =============================================================================
# Async Hook Registry
# =============================================================================


@dataclass
class PendingAsyncHook:
    """A pending async (background) hook process."""

    process_id: str
    hook_id: str
    hook_name: str
    hook_event: str
    start_time: float
    timeout: float
    command: str
    response_attached: bool = False
    tool_name: str | None = None
    plugin_id: str | None = None
    stop_progress_interval: Callable[[], None] | None = None
    stdout_buffer: str = ""
    stderr_buffer: str = ""


class AsyncHookRegistry:
    """Registry for pending async hook processes.

    Manages background hook processes that run asynchronously and may
    return results after the main execution flow continues.
    """

    def __init__(self) -> None:
        self._pending: dict[str, PendingAsyncHook] = {}
        self._progress_interval: float = 1.0  # seconds

    def register(
        self,
        process_id: str,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        command: str,
        timeout: float = 15.0,
        tool_name: str | None = None,
        plugin_id: str | None = None,
        stop_interval: Callable[[], None] | None = None,
    ) -> None:
        """Register a pending async hook."""
        hook = PendingAsyncHook(
            process_id=process_id,
            hook_id=hook_id,
            hook_name=hook_name,
            hook_event=hook_event,
            start_time=time.time(),
            timeout=timeout,
            command=command,
            tool_name=tool_name,
            plugin_id=plugin_id,
            stop_progress_interval=stop_interval,
        )
        self._pending[process_id] = hook
        logger.debug(
            f"Hooks: Registered async hook {process_id} ({hook_name}) "
            f"with timeout {timeout}s"
        )

    def get(self, process_id: str) -> PendingAsyncHook | None:
        """Get a pending hook by process ID."""
        return self._pending.get(process_id)

    def get_all(self) -> list[PendingAsyncHook]:
        """Get all pending hooks."""
        return list(self._pending.values())

    def get_active(self) -> list[PendingAsyncHook]:
        """Get pending hooks that haven't delivered responses."""
        return [h for h in self._pending.values() if not h.response_attached]

    def mark_attached(self, process_id: str) -> None:
        """Mark a hook as having delivered its response."""
        if process_id in self._pending:
            self._pending[process_id].response_attached = True

    def remove(self, process_id: str) -> None:
        """Remove a hook from the registry."""
        if process_id in self._pending:
            hook = self._pending[process_id]
            if hook.stop_progress_interval:
                hook.stop_progress_interval()
            del self._pending[process_id]
            logger.debug(f"Hooks: Removed hook {process_id} ({hook.hook_name})")

    def check_timeout(self) -> list[str]:
        """Return process IDs of timed-out hooks."""
        timed_out = []
        now = time.time()
        for process_id, hook in list(self._pending.items()):
            if now - hook.start_time > hook.timeout:
                timed_out.append(process_id)
        return timed_out

    def clear(self) -> None:
        """Clear all pending hooks."""
        for hook in self._pending.values():
            if hook.stop_progress_interval:
                hook.stop_progress_interval()
        self._pending.clear()

    def __len__(self) -> int:
        return len(self._pending)


# Global async hook registry
_async_hook_registry = AsyncHookRegistry()


def get_async_hook_registry() -> AsyncHookRegistry:
    """Get the global AsyncHookRegistry instance."""
    return _async_hook_registry


# =============================================================================
# Session Hooks (ephemeral in-memory hooks)
# =============================================================================


@dataclass
class FunctionHook:
    """A function-based hook callback (Python, in-memory only)."""

    id: str
    callback: Callable[..., Awaitable[bool] | bool]
    timeout: float = 5.0
    error_message: str = ""
    status_message: str = ""


@dataclass
class SessionHookEntry:
    """A single hook entry with optional success callback."""

    hook: HookCommand | FunctionHook
    on_success: Callable[[HookOutput], None] | None = None


@dataclass
class SessionHookMatcher:
    """Hooks grouped by matcher pattern."""

    matcher: str
    skill_root: str | None = None
    hooks: list[SessionHookEntry] = field(default_factory=list)


@dataclass
class SessionHookStore:
    """Per-session hook storage."""

    hooks: dict[str, list[SessionHookMatcher]] = field(default_factory=dict)


class SessionHookManager:
    """Manager for session-scoped ephemeral hooks.

    Session hooks are temporary, in-memory only, and cleared when
    the session ends. They support both command hooks (shell commands)
    and function hooks (Python callbacks).

    Uses a dict-of-lists structure where keys are hook event names,
    matching the TypeScript SessionHooksState pattern.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionHookStore] = {}

    def add_session(self, session_id: str) -> None:
        """Create a new session hook store."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionHookStore()
            logger.debug(f"Hooks: Created session store for {session_id}")

    def remove_session(self, session_id: str) -> None:
        """Remove a session and all its hooks."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.debug(f"Hooks: Removed session store for {session_id}")

    def add_command_hook(
        self,
        session_id: str,
        event: HookEvent,
        matcher: str,
        command: str,
        prompt: str | None = None,
        on_success: Callable[[HookOutput], None] | None = None,
        skill_root: str | None = None,
    ) -> None:
        """Add a command hook to a session."""
        self.add_session(session_id)
        store = self._sessions[session_id]
        event_key = event.value

        matchers = store.hooks.get(event_key, [])
        # Find existing matcher with same pattern
        existing = None
        for m in matchers:
            if m.matcher == matcher and m.skill_root == skill_root:
                existing = m
                break

        if existing:
            existing.hooks.append(SessionHookEntry(
                hook=HookCommand(command=command, prompt=prompt),
                on_success=on_success,
            ))
        else:
            matchers.append(SessionHookMatcher(
                matcher=matcher,
                skill_root=skill_root,
                hooks=[SessionHookEntry(
                    hook=HookCommand(command=command, prompt=prompt),
                    on_success=on_success,
                )],
            ))
        store.hooks[event_key] = matchers
        logger.debug(
            f"Hooks: Added command hook for {event.value} "
            f"(matcher='{matcher}') in session {session_id}"
        )

    def add_function_hook(
        self,
        session_id: str,
        event: HookEvent,
        matcher: str,
        callback: Callable[..., Awaitable[bool] | bool],
        error_message: str = "",
        timeout: float = 5.0,
        hook_id: str | None = None,
    ) -> str:
        """Add a function hook to a session. Returns the hook ID."""
        hook_id = hook_id or f"fn-hook-{uuid.uuid4().hex[:12]}"
        self.add_session(session_id)
        store = self._sessions[session_id]
        event_key = event.value

        function_hook = FunctionHook(
            id=hook_id,
            callback=callback,
            timeout=timeout,
            error_message=error_message,
        )

        matchers = store.hooks.get(event_key, [])
        # Find existing matcher
        existing = None
        for m in matchers:
            if m.matcher == matcher:
                existing = m
                break

        if existing:
            existing.hooks.append(SessionHookEntry(hook=function_hook))
        else:
            matchers.append(SessionHookMatcher(
                matcher=matcher,
                hooks=[SessionHookEntry(hook=function_hook)],
            ))
        store.hooks[event_key] = matchers
        logger.debug(
            f"Hooks: Added function hook {hook_id} for {event.value} "
            f"(matcher='{matcher}') in session {session_id}"
        )
        return hook_id

    def remove_function_hook(
        self,
        session_id: str,
        event: HookEvent,
        hook_id: str,
    ) -> bool:
        """Remove a function hook by ID. Returns True if found and removed."""
        if session_id not in self._sessions:
            return False
        store = self._sessions[session_id]
        event_key = event.value

        matchers = store.hooks.get(event_key, [])
        removed = False
        for matcher in matchers:
            original_len = len(matcher.hooks)
            matcher.hooks = [
                e for e in matcher.hooks
                if not (isinstance(e.hook, FunctionHook) and e.hook.id == hook_id)
            ]
            if len(matcher.hooks) < original_len:
                removed = True

        # Clean up empty matchers
        store.hooks[event_key] = [m for m in matchers if m.hooks]

        if removed:
            logger.debug(
                f"Hooks: Removed function hook {hook_id} "
                f"for {event.value} in session {session_id}"
            )
        return removed

    def get_hooks_for_event(
        self,
        session_id: str,
        event: HookEvent,
    ) -> list[SessionHookMatcher]:
        """Get all hook matchers for a specific event in a session."""
        if session_id not in self._sessions:
            return []
        return self._sessions[session_id].hooks.get(event.value, [])

    def get_function_hooks_for_event(
        self,
        session_id: str,
        event: HookEvent,
    ) -> list[tuple[str, FunctionHook]]:
        """Get function hooks (id, hook) for a specific event."""
        results: list[tuple[str, FunctionHook]] = []
        for matcher in self.get_hooks_for_event(session_id, event):
            for entry in matcher.hooks:
                if isinstance(entry.hook, FunctionHook):
                    results.append((matcher.matcher, entry.hook))
        return results

    def clear_session(self, session_id: str) -> None:
        """Clear all hooks for a session."""
        self.remove_session(session_id)
        logger.debug(f"Hooks: Cleared all hooks for session {session_id}")

    def __len__(self) -> int:
        return len(self._sessions)


# =============================================================================
# Hook Manager (main entry point)
# =============================================================================


class HookManager:
    """Main entry point for the hook system.

    Coordinates the event emitter, async hook registry, and session hooks.
    Provides a unified API for hook registration and execution.

    Example:
        manager = HookManager()

        # Execute pre-tool-use hooks
        results = await manager.execute_hooks(
            event=HookEvent.PRE_TOOL_USE,
            input=HookInput(
                tool_name="bash",
                tool_input={"command": "ls"},
                tool_use_id="use-123",
            ),
        )
    """

    def __init__(self) -> None:
        self.events = _hook_event_emitter
        self.async_registry = _async_hook_registry
        self.session_hooks = SessionHookManager()
        self._progress_tasks: dict[str, asyncio.Task[None]] = {}

    def enable_all_events(self) -> None:
        """Enable emission of all hook execution events."""
        self.events.set_all_events_enabled(True)

    def disable_all_events(self) -> None:
        """Disable emission of non-essential hook execution events."""
        self.events.set_all_events_enabled(False)

    def set_event_handler(
        self,
        handler: HookEventHandler | None,
    ) -> None:
        """Register a handler for hook execution events."""
        self.events.set_handler(handler)

    async def execute_command_hook(
        self,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        command: str,
        hook_input: HookInput,
        timeout: float = 30.0,
    ) -> HookOutput:
        """Execute a command hook asynchronously.

        Args:
            hook_id: Unique identifier for this hook execution.
            hook_name: Human-readable name of the hook.
            hook_event: The event type being executed.
            command: Shell command to run.
            hook_input: Input data to pass to the hook (as JSON on stdin).
            timeout: Command timeout in seconds.

        Returns:
            HookOutput with stdout, stderr, exit_code, and parsed JSON.
        """
        self.events.emit_started(hook_id, hook_name, hook_event)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            input_json = hook_input.to_json()
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(input_json.encode()),
                timeout=timeout,
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode or 0

            # Parse JSON output if present
            json_output: dict[str, Any] | None = None
            for line in stdout.split("\n"):
                stripped = line.strip()
                if stripped.startswith("{"):
                    try:
                        json_output = json.loads(stripped)
                        break
                    except json.JSONDecodeError:
                        pass

            outcome = "success" if exit_code == 0 else "error"
            self.events.emit_response(
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=hook_event,
                output=stdout + stderr,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                outcome=outcome,
            )

            return HookOutput(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                json_output=json_output,
            )

        except TimeoutError:
            self.events.emit_response(
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=hook_event,
                output="",
                stdout="",
                stderr=f"Hook timed out after {timeout}s",
                exit_code=124,
                outcome="error",
            )
            return HookOutput(
                stdout="",
                stderr=f"Hook timed out after {timeout}s",
                exit_code=124,
                json_output=None,
            )
        except Exception as e:
            self.events.emit_response(
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=hook_event,
                output="",
                stdout="",
                stderr=str(e),
                exit_code=1,
                outcome="error",
            )
            return HookOutput(
                stdout="",
                stderr=str(e),
                exit_code=1,
                json_output=None,
            )

    async def execute_function_hook(
        self,
        hook: FunctionHook,
        args: dict[str, Any],
    ) -> tuple[bool, str]:
        """Execute a function hook callback.

        Args:
            hook: The function hook to execute.
            args: Arguments to pass to the callback.

        Returns:
            Tuple of (result, error_message).
        """
        try:
            if asyncio.iscoroutinefunction(hook.callback):
                result = await hook.callback(**args)
            else:
                result = hook.callback(**args)

            if asyncio.iscoroutine(result):
                result = await result

            return bool(result), ""
        except Exception as e:
            return False, hook.error_message or str(e)

    async def check_async_hook_responses(
        self,
    ) -> list[dict[str, Any]]:
        """Check all pending async hooks for completed responses.

        This should be called periodically (e.g., in a background task)
        to collect responses from background hook processes.

        Returns:
            List of response dicts with process_id, response, hook_name, etc.
        """
        responses = []
        emitter = get_hook_event_emitter()

        for hook in list(self.async_registry.get_active()):
            if hook.response_attached:
                continue

            # Check for timeout
            elapsed = time.time() - hook.start_time
            if elapsed > hook.timeout:
                logger.debug(
                    f"Hooks: Async hook {hook.process_id} timed out "
                    f"(elapsed={elapsed:.1f}s)"
                )
                self.async_registry.remove(hook.process_id)
                emitter.emit_response(
                    hook_id=hook.hook_id,
                    hook_name=hook.hook_name,
                    hook_event=hook.hook_event,
                    output="",
                    stdout="",
                    stderr="Hook timed out",
                    exit_code=124,
                    outcome="cancelled",
                )
                continue

            # Collect output from stdout_buffer
            # (In real implementation, this would read from a subprocess pipe)
            if hook.stdout_buffer:
                for line in hook.stdout_buffer.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("{"):
                        try:
                            response = json.loads(stripped)
                            hook.response_attached = True
                            self.async_registry.mark_attached(hook.process_id)
                            emitter.emit_response(
                                hook_id=hook.hook_id,
                                hook_name=hook.hook_name,
                                hook_event=hook.hook_event,
                                output=hook.stdout_buffer + hook.stderr_buffer,
                                stdout=hook.stdout_buffer,
                                stderr=hook.stderr_buffer,
                                exit_code=0,
                                outcome="success",
                            )
                            responses.append({
                                "process_id": hook.process_id,
                                "response": response,
                                "hook_name": hook.hook_name,
                                "hook_event": hook.hook_event,
                                "tool_name": hook.tool_name,
                                "plugin_id": hook.plugin_id,
                                "stdout": hook.stdout_buffer,
                                "stderr": hook.stderr_buffer,
                            })
                            break
                        except json.JSONDecodeError:
                            pass

        return responses

    def clear(self) -> None:
        """Clear all hook state."""
        self.events.clear()
        self.async_registry.clear()
        for task in self._progress_tasks.values():
            task.cancel()
        self._progress_tasks.clear()


# =============================================================================
# Hook Event Metadata Registry
# =============================================================================


# All hook events and their metadata
_HOOK_EVENT_METADATA: dict[str, HookEventMetadata] = {
    HookEvent.PRE_TOOL_USE: HookEventMetadata(
        summary="Before tool execution",
        description=(
            "Input to command is JSON of tool call arguments.\n"
            "Exit code 0 - stdout/stderr not shown\n"
            "Exit code 2 - show stderr to model and block tool call\n"
            "Other exit codes - show stderr to user only but continue with tool call"
        ),
        matcher_metadata=MatcherMetadata(field_to_match="tool_name", values=[]),
    ),
    HookEvent.POST_TOOL_USE: HookEventMetadata(
        summary="After tool execution",
        description=(
            "Input to command is JSON with fields 'inputs' (tool call arguments) "
            "and 'response' (tool call response).\n"
            "Exit code 0 - stdout shown in transcript mode (ctrl+o)\n"
            "Exit code 2 - show stderr to model immediately\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(field_to_match="tool_name", values=[]),
    ),
    HookEvent.POST_TOOL_USE_FAILURE: HookEventMetadata(
        summary="After tool execution fails",
        description=(
            "Input to command is JSON with tool_name, tool_input, tool_use_id, "
            "error, error_type, is_interrupt, and is_timeout.\n"
            "Exit code 0 - stdout shown in transcript mode (ctrl+o)\n"
            "Exit code 2 - show stderr to model immediately\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(field_to_match="tool_name", values=[]),
    ),
    HookEvent.PERMISSION_DENIED: HookEventMetadata(
        summary="After auto mode classifier denies a tool call",
        description=(
            "Input to command is JSON with tool_name, tool_input, tool_use_id, "
            "and reason.\n"
            "Return {'hookSpecificOutput': {'hookEventName': 'PermissionDenied', "
            "'retry': True}} to tell the model it may retry.\n"
            "Exit code 0 - stdout shown in transcript mode (ctrl+o)\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(field_to_match="tool_name", values=[]),
    ),
    HookEvent.NOTIFICATION: HookEventMetadata(
        summary="When notifications are sent",
        description=(
            "Input to command is JSON with notification message and type.\n"
            "Exit code 0 - stdout/stderr not shown\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="notification_type",
            values=[
                "permission_prompt", "idle_prompt", "auth_success",
                "elicitation_dialog", "elicitation_complete",
                "elicitation_response",
            ],
        ),
    ),
    HookEvent.USER_PROMPT_SUBMIT: HookEventMetadata(
        summary="When the user submits a prompt",
        description=(
            "Input to command is JSON with original user prompt text.\n"
            "Exit code 0 - stdout shown to Claude\n"
            "Exit code 2 - block processing, erase original prompt, "
            "and show stderr to user only\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.SESSION_START: HookEventMetadata(
        summary="When a new session is started",
        description=(
            "Input to command is JSON with session start source.\n"
            "Exit code 0 - stdout shown to Claude\n"
            "Blocking errors are ignored\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="source",
            values=["startup", "resume", "clear", "compact"],
        ),
    ),
    HookEvent.SESSION_END: HookEventMetadata(
        summary="When a session is ending",
        description=(
            "Input to command is JSON with session end reason.\n"
            "Exit code 0 - command completes successfully\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="reason",
            values=["clear", "logout", "prompt_input_exit", "other"],
        ),
    ),
    HookEvent.STOP: HookEventMetadata(
        summary="Right before Claude concludes its response",
        description=(
            "Exit code 0 - stdout/stderr not shown\n"
            "Exit code 2 - show stderr to model and continue conversation\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.STOP_FAILURE: HookEventMetadata(
        summary="When the turn ends due to an API error",
        description=(
            "Fires instead of Stop when an API error (rate limit, auth failure, etc.) "
            "ended the turn. Fire-and-forget — hook output and exit codes ignored."
        ),
    ),
    HookEvent.SUBAGENT_START: HookEventMetadata(
        summary="When a subagent (Agent tool call) is started",
        description=(
            "Input to command is JSON with agent_id and agent_type.\n"
            "Exit code 0 - stdout shown to subagent\n"
            "Blocking errors are ignored\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.SUBAGENT_STOP: HookEventMetadata(
        summary="Right before a subagent concludes its response",
        description=(
            "Input to command is JSON with agent_id, agent_type, "
            "and agent_transcript_path.\n"
            "Exit code 0 - stdout/stderr not shown\n"
            "Exit code 2 - show stderr to subagent and continue having it run\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.PRE_COMPACT: HookEventMetadata(
        summary="Before conversation compaction",
        description=(
            "Input to command is JSON with compaction details.\n"
            "Exit code 0 - stdout appended as custom compact instructions\n"
            "Exit code 2 - block compaction\n"
            "Other exit codes - show stderr to user only but continue with compaction"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="trigger",
            values=["manual", "auto"],
        ),
    ),
    HookEvent.POST_COMPACT: HookEventMetadata(
        summary="After conversation compaction",
        description=(
            "Input to command is JSON with compaction details and the summary.\n"
            "Exit code 0 - stdout shown to user\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="trigger",
            values=["manual", "auto"],
        ),
    ),
    HookEvent.PERMISSION_REQUEST: HookEventMetadata(
        summary="When a permission dialog is displayed",
        description=(
            "Input to command is JSON with tool_name, tool_input, and tool_use_id.\n"
            "Output JSON with hookSpecificOutput containing decision to allow or deny.\n"
            "Exit code 0 - use hook decision if provided\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(field_to_match="tool_name", values=[]),
    ),
    HookEvent.SETUP: HookEventMetadata(
        summary="Repo setup hooks for init and maintenance",
        description=(
            "Input to command is JSON with trigger (init or maintenance).\n"
            "Exit code 0 - stdout shown to Claude\n"
            "Blocking errors are ignored\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="trigger",
            values=["init", "maintenance"],
        ),
    ),
    HookEvent.TEAMMATE_IDLE: HookEventMetadata(
        summary="When a teammate is about to go idle",
        description=(
            "Input to command is JSON with teammate_name and team_name.\n"
            "Exit code 0 - stdout/stderr not shown\n"
            "Exit code 2 - show stderr to teammate and prevent idle\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.TASK_CREATED: HookEventMetadata(
        summary="When a task is being created",
        description=(
            "Input to command is JSON with task_id, task_subject, "
            "task_description, teammate_name, and team_name.\n"
            "Exit code 0 - stdout/stderr not shown\n"
            "Exit code 2 - show stderr to model and prevent task creation\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.TASK_COMPLETED: HookEventMetadata(
        summary="When a task is being marked as completed",
        description=(
            "Input to command is JSON with task_id, task_subject, "
            "task_description, teammate_name, and team_name.\n"
            "Exit code 0 - stdout/stderr not shown\n"
            "Exit code 2 - show stderr to model and prevent task completion\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.ELICITATION: HookEventMetadata(
        summary="When an MCP server requests user input (elicitation)",
        description=(
            "Input to command is JSON with mcp_server_name, message, "
            "and requested_schema.\n"
            "Output JSON with hookSpecificOutput containing "
            "action (accept/decline/cancel) and optional content.\n"
            "Exit code 0 - use hook response if provided\n"
            "Exit code 2 - deny the elicitation\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.ELICITATION_RESULT: HookEventMetadata(
        summary="After a user responds to an MCP elicitation",
        description=(
            "Input to command is JSON with mcp_server_name, action, content, "
            "mode, and elicitation_id.\n"
            "Output JSON with hookSpecificOutput containing optional "
            "action and content to override the response.\n"
            "Exit code 0 - use hook response if provided\n"
            "Exit code 2 - block the response (action becomes decline)\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.CONFIG_CHANGE: HookEventMetadata(
        summary="When configuration files change during a session",
        description=(
            "Input to command is JSON with source and file_path.\n"
            "Exit code 0 - allow the change\n"
            "Exit code 2 - block the change from being applied to the session\n"
            "Other exit codes - show stderr to user only"
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="source",
            values=[
                "user_settings", "project_settings", "local_settings",
                "policy_settings", "skills",
            ],
        ),
    ),
    HookEvent.INSTRUCTIONS_LOADED: HookEventMetadata(
        summary="When an instruction file (CLAUDE.md or rule) is loaded",
        description=(
            "Input to command is JSON with file_path, memory_type, load_reason, etc.\n"
            "Exit code 0 - command completes successfully\n"
            "Other exit codes - show stderr to user only\n"
            "This hook is observability-only and does not support blocking."
        ),
        matcher_metadata=MatcherMetadata(
            field_to_match="load_reason",
            values=[
                "session_start", "nested_traversal", "path_glob_match",
                "include", "compact",
            ],
        ),
    ),
    HookEvent.WORKTREE_CREATE: HookEventMetadata(
        summary="Create an isolated worktree for VCS-agnostic isolation",
        description=(
            "Input to command is JSON with name (suggested worktree slug).\n"
            "Stdout should contain the absolute path to the created worktree directory.\n"
            "Exit code 0 - worktree created successfully\n"
            "Other exit codes - worktree creation failed"
        ),
    ),
    HookEvent.WORKTREE_REMOVE: HookEventMetadata(
        summary="Remove a previously created worktree",
        description=(
            "Input to command is JSON with worktree_path.\n"
            "Exit code 0 - worktree removed successfully\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.CWD_CHANGED: HookEventMetadata(
        summary="After the working directory changes",
        description=(
            "Input to command is JSON with old_cwd and new_cwd.\n"
            "Hook output can include hookSpecificOutput.watchPaths "
            "to register with the FileChanged watcher.\n"
            "Exit code 0 - command completes successfully\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
    HookEvent.FILE_CHANGED: HookEventMetadata(
        summary="When a watched file changes",
        description=(
            "Input to command is JSON with file_path and event (change, add, unlink).\n"
            "The matcher field specifies filenames to watch.\n"
            "Exit code 0 - command completes successfully\n"
            "Other exit codes - show stderr to user only"
        ),
    ),
}


def get_hook_event_metadata(event: HookEvent) -> HookEventMetadata:
    """Get metadata for a hook event."""
    return _HOOK_EVENT_METADATA.get(event.value, HookEventMetadata(
        summary=event.value,
        description="",
    ))


def get_all_hook_events() -> list[str]:
    """Get all registered hook event names."""
    return ALL_HOOK_EVENTS
