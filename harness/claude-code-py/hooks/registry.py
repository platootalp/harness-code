"""
Async Hook Registry for Claude Code.

Manages pending async hooks, tracks their execution state, checks for responses,
and emits hook lifecycle events.

Migrated from src/utils/hooks/AsyncHookRegistry.ts and src/utils/hooks/hookEvents.ts.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# ============================================================================
# Hook Event Types
# ============================================================================


class HookExecutionEventType(Enum):
    """Types of hook execution lifecycle events."""

    STARTED = "started"
    PROGRESS = "progress"
    RESPONSE = "response"


@dataclass(frozen=True)
class MatcherMetadata:
    """Metadata about matchers for a hook event."""

    field_to_match: str
    values: list[str]


@dataclass(frozen=True)
class HookEventMetadata:
    """Metadata describing a hook event for display in the UI."""

    summary: str
    description: str
    matcher_metadata: MatcherMetadata | None = None


# ============================================================================
# Hook Execution Events
# ============================================================================


@dataclass
class HookStartedEvent:
    """Event emitted when a hook starts executing."""

    type: HookExecutionEventType = field(default=HookExecutionEventType.STARTED)
    hook_id: str = ""
    hook_name: str = ""
    hook_event: str = ""


@dataclass
class HookProgressEvent:
    """Event emitted periodically while a hook is running."""

    type: HookExecutionEventType = field(default=HookExecutionEventType.PROGRESS)
    hook_id: str = ""
    hook_name: str = ""
    hook_event: str = ""
    stdout: str = ""
    stderr: str = ""
    output: str = ""


@dataclass
class HookResponseEvent:
    """Event emitted when a hook completes with its response."""

    type: HookExecutionEventType = field(default=HookExecutionEventType.RESPONSE)
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


# ============================================================================
# Hook Event Metadata Cache
# ============================================================================


class _HookEventMetadataCache:
    """
    Cached metadata for all hook events.

    Uses a sorted tool names key so that callers passing a fresh toolNames
    array each render (e.g., HooksConfigMenu) hit the cache instead of leaking
    a new entry per call.
    """

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, HookEventMetadata]] = {}

    def get(
        self,
        tool_names: list[str],
    ) -> dict[str, HookEventMetadata]:
        """
        Get hook event metadata, using cache when possible.

        Args:
            tool_names: List of tool names for matcher values.

        Returns:
            Dictionary mapping event names to their metadata.
        """
        cache_key = ",".join(sorted(tool_names))
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._build_metadata(tool_names)
        self._cache[cache_key] = result
        return result

    def _build_metadata(
        self,
        tool_names: list[str],
    ) -> dict[str, HookEventMetadata]:
        """Build metadata for all hook events."""
        return {
            "PreToolUse": HookEventMetadata(
                summary="Before tool execution",
                description=(
                    "Input to command is JSON of tool call arguments.\n"
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Exit code 2 - show stderr to model and block tool call\n"
                    "Other exit codes - show stderr to user only but continue with tool call"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="tool_name",
                    values=tool_names,
                ),
            ),
            "PostToolUse": HookEventMetadata(
                summary="After tool execution",
                description=(
                    "Input to command is JSON with fields 'inputs' (tool call arguments) "
                    "and 'response' (tool call response).\n"
                    "Exit code 0 - stdout shown in transcript mode (ctrl+o)\n"
                    "Exit code 2 - show stderr to model immediately\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="tool_name",
                    values=tool_names,
                ),
            ),
            "PostToolUseFailure": HookEventMetadata(
                summary="After tool execution fails",
                description=(
                    "Input to command is JSON with tool_name, tool_input, tool_use_id, "
                    "error, error_type, is_interrupt, and is_timeout.\n"
                    "Exit code 0 - stdout shown in transcript mode (ctrl+o)\n"
                    "Exit code 2 - show stderr to model immediately\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="tool_name",
                    values=tool_names,
                ),
            ),
            "PermissionDenied": HookEventMetadata(
                summary="After auto mode classifier denies a tool call",
                description=(
                    "Input to command is JSON with tool_name, tool_input, tool_use_id, "
                    "and reason.\n"
                    'Return {"hookSpecificOutput":{"hookEventName":"PermissionDenied","retry":true}} '
                    "to tell the model it may retry.\n"
                    "Exit code 0 - stdout shown in transcript mode (ctrl+o)\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="tool_name",
                    values=tool_names,
                ),
            ),
            "Notification": HookEventMetadata(
                summary="When notifications are sent",
                description=(
                    "Input to command is JSON with notification message and type.\n"
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="notification_type",
                    values=[
                        "permission_prompt",
                        "idle_prompt",
                        "auth_success",
                        "elicitation_dialog",
                        "elicitation_complete",
                        "elicitation_response",
                    ],
                ),
            ),
            "UserPromptSubmit": HookEventMetadata(
                summary="When the user submits a prompt",
                description=(
                    "Input to command is JSON with original user prompt text.\n"
                    "Exit code 0 - stdout shown to Claude\n"
                    "Exit code 2 - block processing, erase original prompt, "
                    "and show stderr to user only\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "SessionStart": HookEventMetadata(
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
            "Stop": HookEventMetadata(
                summary="Right before Claude concludes its response",
                description=(
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Exit code 2 - show stderr to model and continue conversation\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "StopFailure": HookEventMetadata(
                summary="When the turn ends due to an API error",
                description=(
                    "Fires instead of Stop when an API error (rate limit, auth failure, etc.) "
                    "ended the turn. Fire-and-forget — hook output and exit codes are ignored."
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="error",
                    values=[
                        "rate_limit",
                        "authentication_failed",
                        "billing_error",
                        "invalid_request",
                        "server_error",
                        "max_output_tokens",
                        "unknown",
                    ],
                ),
            ),
            "SubagentStart": HookEventMetadata(
                summary="When a subagent (Agent tool call) is started",
                description=(
                    "Input to command is JSON with agent_id and agent_type.\n"
                    "Exit code 0 - stdout shown to subagent\n"
                    "Blocking errors are ignored\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="agent_type",
                    values=[],
                ),
            ),
            "SubagentStop": HookEventMetadata(
                summary="Right before a subagent (Agent tool call) concludes its response",
                description=(
                    "Input to command is JSON with agent_id, agent_type, "
                    "and agent_transcript_path.\n"
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Exit code 2 - show stderr to subagent and continue having it run\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="agent_type",
                    values=[],
                ),
            ),
            "PreCompact": HookEventMetadata(
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
            "PostCompact": HookEventMetadata(
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
            "SessionEnd": HookEventMetadata(
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
            "PermissionRequest": HookEventMetadata(
                summary="When a permission dialog is displayed",
                description=(
                    "Input to command is JSON with tool_name, tool_input, and tool_use_id.\n"
                    "Output JSON with hookSpecificOutput containing decision to allow or deny.\n"
                    "Exit code 0 - use hook decision if provided\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="tool_name",
                    values=tool_names,
                ),
            ),
            "Setup": HookEventMetadata(
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
            "TeammateIdle": HookEventMetadata(
                summary="When a teammate is about to go idle",
                description=(
                    "Input to command is JSON with teammate_name and team_name.\n"
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Exit code 2 - show stderr to teammate and prevent idle "
                    "(teammate continues working)\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "TaskCreated": HookEventMetadata(
                summary="When a task is being created",
                description=(
                    "Input to command is JSON with task_id, task_subject, task_description, "
                    "teammate_name, and team_name.\n"
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Exit code 2 - show stderr to model and prevent task creation\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "TaskCompleted": HookEventMetadata(
                summary="When a task is being marked as completed",
                description=(
                    "Input to command is JSON with task_id, task_subject, task_description, "
                    "teammate_name, and team_name.\n"
                    "Exit code 0 - stdout/stderr not shown\n"
                    "Exit code 2 - show stderr to model and prevent task completion\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "Elicitation": HookEventMetadata(
                summary="When an MCP server requests user input (elicitation)",
                description=(
                    "Input to command is JSON with mcp_server_name, message, "
                    "and requested_schema.\n"
                    "Output JSON with hookSpecificOutput containing action "
                    "(accept/decline/cancel) and optional content.\n"
                    "Exit code 0 - use hook response if provided\n"
                    "Exit code 2 - deny the elicitation\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="mcp_server_name",
                    values=[],
                ),
            ),
            "ElicitationResult": HookEventMetadata(
                summary="After a user responds to an MCP elicitation",
                description=(
                    "Input to command is JSON with mcp_server_name, action, content, mode, "
                    "and elicitation_id.\n"
                    "Output JSON with hookSpecificOutput containing optional action "
                    "and content to override the response.\n"
                    "Exit code 0 - use hook response if provided\n"
                    "Exit code 2 - block the response (action becomes decline)\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="mcp_server_name",
                    values=[],
                ),
            ),
            "ConfigChange": HookEventMetadata(
                summary="When configuration files change during a session",
                description=(
                    "Input to command is JSON with source "
                    "(user_settings, project_settings, local_settings, policy_settings, skills) "
                    "and file_path.\n"
                    "Exit code 0 - allow the change\n"
                    "Exit code 2 - block the change from being applied to the session\n"
                    "Other exit codes - show stderr to user only"
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="source",
                    values=[
                        "user_settings",
                        "project_settings",
                        "local_settings",
                        "policy_settings",
                        "skills",
                    ],
                ),
            ),
            "InstructionsLoaded": HookEventMetadata(
                summary="When an instruction file (CLAUDE.md or rule) is loaded",
                description=(
                    "Input to command is JSON with file_path, memory_type "
                    "(User, Project, Local, Managed), load_reason "
                    "(session_start, nested_traversal, path_glob_match, include, compact), "
                    "globs (optional — the paths: frontmatter patterns that matched), "
                    "trigger_file_path (optional — the file Claude touched that caused the load), "
                    "and parent_file_path (optional — the file that @-included this one).\n"
                    "Exit code 0 - command completes successfully\n"
                    "Other exit codes - show stderr to user only\n"
                    "This hook is observability-only and does not support blocking."
                ),
                matcher_metadata=MatcherMetadata(
                    field_to_match="load_reason",
                    values=[
                        "session_start",
                        "nested_traversal",
                        "path_glob_match",
                        "include",
                        "compact",
                    ],
                ),
            ),
            "WorktreeCreate": HookEventMetadata(
                summary="Create an isolated worktree for VCS-agnostic isolation",
                description=(
                    "Input to command is JSON with name (suggested worktree slug).\n"
                    "Stdout should contain the absolute path to the created worktree directory.\n"
                    "Exit code 0 - worktree created successfully\n"
                    "Other exit codes - worktree creation failed"
                ),
            ),
            "WorktreeRemove": HookEventMetadata(
                summary="Remove a previously created worktree",
                description=(
                    "Input to command is JSON with worktree_path "
                    "(absolute path to worktree).\n"
                    "Exit code 0 - worktree removed successfully\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "CwdChanged": HookEventMetadata(
                summary="After the working directory changes",
                description=(
                    "Input to command is JSON with old_cwd and new_cwd.\n"
                    "CLAUDE_ENV_FILE is set — write bash exports there to apply env "
                    "to subsequent BashTool commands.\n"
                    "Hook output can include hookSpecificOutput.watchPaths "
                    "(array of absolute paths) to register with the FileChanged watcher.\n"
                    "Exit code 0 - command completes successfully\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
            "FileChanged": HookEventMetadata(
                summary="When a watched file changes",
                description=(
                    "Input to command is JSON with file_path and event "
                    "(change, add, unlink).\n"
                    "CLAUDE_ENV_FILE is set — write bash exports there to apply env "
                    "to subsequent BashTool commands.\n"
                    "The matcher field specifies filenames to watch in the current "
                    "directory (e.g. '.envrc|.env').\n"
                    "Hook output can include hookSpecificOutput.watchPaths "
                    "(array of absolute paths) to dynamically update the watch list.\n"
                    "Exit code 0 - command completes successfully\n"
                    "Other exit codes - show stderr to user only"
                ),
            ),
        }


# Global cache instance for hook event metadata
_hook_event_metadata_cache = _HookEventMetadataCache()

# Always-emitted hook events (low-noise lifecycle events)
_ALWAYS_EMITTED_HOOK_EVENTS: frozenset[str] = frozenset({"SessionStart", "Setup"})

_MAX_PENDING_EVENTS = 100


# ============================================================================
# Pending Hook Data
# ============================================================================


@dataclass
class PendingAsyncHook:
    """
    Represents an async hook that is currently pending execution.

    Tracks the hook's process ID, metadata, timing, and shell command state.
    """

    process_id: str
    hook_id: str
    hook_name: str
    hook_event: str
    tool_name: str | None = None
    plugin_id: str | None = None
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    timeout: int = 15000  # milliseconds
    command: str = ""
    response_attachment_sent: bool = False
    stop_progress_interval: Callable[[], None] | None = None

    # Shell command result - populated after execution
    shell_result: Any = None  # ShellCommand result
    stdout: str = ""
    stderr: str = ""

    @property
    def is_timed_out(self) -> bool:
        """Check if the hook has exceeded its timeout."""
        elapsed = (datetime.now(UTC) - self.start_time).total_seconds() * 1000
        return elapsed > self.timeout


# ============================================================================
# Hook Registry
# ============================================================================


class HookRegistry:
    """
    Manages pending async hooks, tracks their execution, and emits lifecycle events.

    The registry maintains a map of in-flight async hooks. Each hook can:
    - Report progress via events
    - Return responses via stdout JSON parsing
    - Be checked for completion
    - Be cleaned up when delivered or cancelled

    Migrated from AsyncHookRegistry.ts.
    """

    def __init__(self) -> None:
        self._pending: dict[str, PendingAsyncHook] = {}
        self._event_handler: HookEventHandler | None = None
        self._all_hook_events_enabled: bool = False
        self._pending_events: list[HookExecutionEvent] = []

    # ------------------------------------------------------------------------
    # Pending hook management
    # ------------------------------------------------------------------------

    def register_pending_async_hook(
        self,
        *,
        process_id: str,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        command: str,
        timeout: int = 15000,
        tool_name: str | None = None,
        plugin_id: str | None = None,
        stop_progress_interval: Callable[[], None] | None = None,
    ) -> PendingAsyncHook:
        """
        Register a new pending async hook.

        Args:
            process_id: Unique identifier for this hook execution.
            hook_id: Public hook identifier.
            hook_name: Display name for the hook.
            hook_event: The hook event type (e.g., 'PreToolUse').
            command: The command being executed.
            timeout: Timeout in milliseconds (default 15s).
            tool_name: Optional tool name for tool-related hooks.
            plugin_id: Optional plugin ID.
            stop_progress_interval: Callback to stop progress reporting.

        Returns:
            The registered PendingAsyncHook.
        """
        pending = PendingAsyncHook(
            process_id=process_id,
            hook_id=hook_id,
            hook_name=hook_name,
            hook_event=hook_event,
            tool_name=tool_name,
            plugin_id=plugin_id,
            timeout=timeout,
            command=command,
            start_time=datetime.now(UTC),
            stop_progress_interval=stop_progress_interval,
        )
        self._pending[process_id] = pending
        return pending

    def get_pending_async_hooks(self) -> list[PendingAsyncHook]:
        """
        Get all pending async hooks that haven't had their response attached.

        Returns:
            List of pending hooks.
        """
        return [h for h in self._pending.values() if not h.response_attachment_sent]

    def remove_pending_hook(self, process_id: str) -> None:
        """Remove a pending hook by process ID."""
        if process_id in self._pending:
            hook = self._pending[process_id]
            if hook.stop_progress_interval:
                hook.stop_progress_interval()
            del self._pending[process_id]

    # ------------------------------------------------------------------------
    # Response checking
    # ------------------------------------------------------------------------

    def check_for_async_hook_responses(
        self,
        get_shell_result: Callable[
            [str], tuple[int, str, str] | None
        ],
    ) -> list[dict[str, Any]]:
        """
        Check all pending hooks for completed responses.

        Args:
            get_shell_result: Callback that takes a process_id and returns
                (exit_code, stdout, stderr) if the shell command has completed,
                or None if still running.

        Returns:
            List of response dictionaries from hooks that have completed
            and returned JSON output.
        """
        responses: list[dict[str, Any]] = []
        to_remove: list[str] = []

        for process_id, hook in list(self._pending.items()):
            if hook.response_attachment_sent:
                continue

            result = get_shell_result(process_id)

            # Still running
            if result is None:
                continue

            exit_code, stdout, stderr = result

            # Shell was killed
            if exit_code < 0:
                self._finalize_hook(hook, exit_code, "cancelled")
                to_remove.append(process_id)
                continue

            # Check for JSON response in stdout
            response = self._parse_json_response(stdout)

            hook.response_attachment_sent = True
            self._finalize_hook(hook, exit_code, "success" if exit_code == 0 else "error")

            responses.append({
                "process_id": process_id,
                "response": response,
                "hook_name": hook.hook_name,
                "hook_event": hook.hook_event,
                "tool_name": hook.tool_name,
                "plugin_id": hook.plugin_id,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
            })

            to_remove.append(process_id)

        # Clean up processed hooks
        for process_id in to_remove:
            if process_id in self._pending:
                hook = self._pending[process_id]
                if hook.stop_progress_interval:
                    hook.stop_progress_interval()
                del self._pending[process_id]

        return responses

    def _parse_json_response(self, stdout: str) -> dict[str, Any]:
        """
        Parse JSON response from hook stdout.

        Looks for lines starting with '{' and tries to parse them as JSON.
        Returns an empty dict if no valid JSON is found.

        Args:
            stdout: The stdout from the hook command.

        Returns:
            Parsed JSON object, or empty dict.
        """
        for line in stdout.split("\n"):
            stripped = line.strip()
            if stripped.startswith("{"):
                try:
                    parsed = json.loads(stripped)
                    # Skip async responses - only want sync responses
                    if not isinstance(parsed, dict) or "async" not in parsed:
                        return parsed
                except json.JSONDecodeError:
                    pass
        return {}

    def _finalize_hook(
        self,
        hook: PendingAsyncHook,
        exit_code: int,
        outcome: str,
    ) -> None:
        """Finalize a hook and emit its response event."""
        if hook.stop_progress_interval:
            hook.stop_progress_interval()

        self._emit_response(
            hook_id=hook.hook_id,
            hook_name=hook.hook_name,
            hook_event=hook.hook_event,
            output=hook.stdout + hook.stderr,
            stdout=hook.stdout,
            stderr=hook.stderr,
            exit_code=exit_code,
            outcome=outcome,
        )

    def remove_delivered_async_hooks(self, process_ids: list[str]) -> None:
        """
        Remove hooks that have already been delivered.

        Args:
            process_ids: List of process IDs to remove.
        """
        for process_id in process_ids:
            if process_id in self._pending:
                hook = self._pending[process_id]
                if hook.response_attachment_sent:
                    if hook.stop_progress_interval:
                        hook.stop_progress_interval()
                    del self._pending[process_id]

    def finalize_pending_async_hooks(
        self,
        get_shell_result: Callable[
            [str], tuple[int, str, str] | None
        ],
    ) -> None:
        """
        Finalize all pending async hooks at session end.

        Runs all hooks to completion or cancels them.

        Args:
            get_shell_result: Callback that takes a process_id and returns
                (exit_code, stdout, stderr) if available.
        """
        for hook in list(self._pending.values()):
            if get_shell_result(hook.process_id) is not None:
                exit_code, stdout, stderr = get_shell_result(hook.process_id)  # type: ignore
                hook.stdout = stdout
                hook.stderr = stderr
                self._finalize_hook(
                    hook,
                    exit_code,
                    "success" if exit_code == 0 else "error",
                )
            else:
                self._finalize_hook(hook, 1, "cancelled")

        self._pending.clear()

    def clear_all_async_hooks(self) -> None:
        """Clear all pending hooks (for testing)."""
        for hook in self._pending.values():
            if hook.stop_progress_interval:
                hook.stop_progress_interval()
        self._pending.clear()

    # ------------------------------------------------------------------------
    # Event system
    # ------------------------------------------------------------------------

    def set_event_handler(self, handler: HookEventHandler | None) -> None:
        """
        Set the handler for hook execution events.

        Args:
            handler: Callback to receive hook lifecycle events, or None to clear.
        """
        self._event_handler = handler
        if handler and self._pending_events:
            for event in self._pending_events:
                handler(event)
            self._pending_events.clear()

    def set_all_hook_events_enabled(self, enabled: bool) -> None:
        """
        Enable emission of all hook event types.

        By default, only SessionStart and Setup events are emitted.
        Call this with True when includeHookEvents is set or in remote mode.

        Args:
            enabled: Whether to enable all hook events.
        """
        self._all_hook_events_enabled = enabled

    def clear_hook_event_state(self) -> None:
        """Reset event state (for testing)."""
        self._event_handler = None
        self._pending_events.clear()
        self._all_hook_events_enabled = False

    def _should_emit(self, hook_event: str) -> bool:
        """Check if an event should be emitted."""
        if hook_event in _ALWAYS_EMITTED_HOOK_EVENTS:
            return True
        return self._all_hook_events_enabled

    def _emit(self, event: HookExecutionEvent) -> None:
        """Emit a hook event to the handler or queue it."""
        if self._event_handler:
            self._event_handler(event)
        else:
            self._pending_events.append(event)
            if len(self._pending_events) > _MAX_PENDING_EVENTS:
                self._pending_events.pop(0)

    def emit_hook_started(
        self,
        hook_id: str,
        hook_name: str,
        hook_event: str,
    ) -> None:
        """Emit a hook started event."""
        if not self._should_emit(hook_event):
            return
        self._emit(
            HookStartedEvent(
                type=HookExecutionEventType.STARTED,
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=hook_event,
            )
        )

    def emit_hook_progress(
        self,
        *,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        stdout: str,
        stderr: str,
        output: str,
    ) -> None:
        """Emit a hook progress event."""
        if not self._should_emit(hook_event):
            return
        self._emit(
            HookProgressEvent(
                type=HookExecutionEventType.PROGRESS,
                hook_id=hook_id,
                hook_name=hook_name,
                hook_event=hook_event,
                stdout=stdout,
                stderr=stderr,
                output=output,
            )
        )

    def _emit_response(
        self,
        *,
        hook_id: str,
        hook_name: str,
        hook_event: str,
        output: str,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        outcome: str,
    ) -> None:
        """Emit a hook response event."""
        # Always emit to pending_events for debugging (unconditionally)
        # This is stored separately from the filtered emission
        if self._should_emit(hook_event) and self._event_handler:
            self._event_handler(
                HookResponseEvent(
                    type=HookExecutionEventType.RESPONSE,
                    hook_id=hook_id,
                    hook_name=hook_name,
                    hook_event=hook_event,
                    output=output,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    outcome=outcome,
                )
            )


# ============================================================================
# Module-level functions
# ============================================================================

# Global registry instance
_global_registry: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    """Get the global hook registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = HookRegistry()
    return _global_registry


def get_hook_event_metadata(
    tool_names: list[str],
) -> dict[str, HookEventMetadata]:
    """
    Get hook event metadata, cached by sorted tool names.

    Args:
        tool_names: List of tool names for matcher values.

    Returns:
        Dictionary mapping event names to their metadata.
    """
    return _hook_event_metadata_cache.get(tool_names)


def get_matcher_metadata(
    event: str,
    tool_names: list[str],
) -> MatcherMetadata | None:
    """
    Get matcher metadata for a specific event.

    Args:
        event: The hook event name.
        tool_names: List of tool names.

    Returns:
        MatcherMetadata if the event has matchers, None otherwise.
    """
    metadata = get_hook_event_metadata(tool_names)
    return metadata.get(event, None)  # type: ignore
