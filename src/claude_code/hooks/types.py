"""
Hook type definitions for the Claude Code hook system.

This module provides Python type definitions for the hook system, enabling
external hooks (command, prompt, agent, HTTP) to intercept and modify execution
at defined points (PreToolUse, UserPromptSubmit, SessionStart, etc.).

Ported from TypeScript src/types/hooks.ts and src/entrypoints/sdk/coreSchemas.ts.

Security: Hooks run external commands/scripts with user-controlled input.
All hook execution is sandboxed and permission-checked before invocation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass


# =============================================================================
# Hook Events (StrEnum)
# =============================================================================

# All valid hook event names, matching TypeScript HOOK_EVENTS
_HOOK_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "Notification",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "Stop",
    "StopFailure",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "PostCompact",
    "PermissionRequest",
    "PermissionDenied",
    "Setup",
    "TeammateIdle",
    "TaskCreated",
    "TaskCompleted",
    "Elicitation",
    "ElicitationResult",
    "ConfigChange",
    "WorktreeCreate",
    "WorktreeRemove",
    "InstructionsLoaded",
    "CwdChanged",
    "FileChanged",
]


class HookEvent(StrEnum):
    """Hook event names that can trigger hook execution."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
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
    PERMISSION_DENIED = "PermissionDenied"
    SETUP = "Setup"
    TEAMMATE_IDLE = "TeammateIdle"
    TASK_CREATED = "TaskCreated"
    TASK_COMPLETED = "TaskCompleted"
    ELICITATION = "Elicitation"
    ELICITATION_RESULT = "ElicitationResult"
    CONFIG_CHANGE = "ConfigChange"
    WORKTREE_CREATE = "WorktreeCreate"
    WORKTREE_REMOVE = "WorktreeRemove"
    INSTRUCTIONS_LOADED = "InstructionsLoaded"
    CWD_CHANGED = "CwdChanged"
    FILE_CHANGED = "FileChanged"


# Runtime constant matching the TypeScript HOOK_EVENTS array
HOOK_EVENTS: list[str] = _HOOK_EVENTS


def is_hook_event(value: str) -> bool:
    """Type guard: check if a string is a valid HookEvent value."""
    return value in _HOOK_EVENTS


# =============================================================================
# Permission Types (shared with permission system)
# =============================================================================

PermissionBehavior = Literal["allow", "deny", "ask"]


class PermissionMode(StrEnum):
    """Permission mode controlling how tool executions are handled."""

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS_PERMISSIONS = "bypassPermissions"
    PLAN = "plan"
    DONT_ASK = "dontAsk"


# =============================================================================
# Base Hook Input
# =============================================================================


@dataclass
class BaseHookInput:
    """Base input fields common to all hook events."""

    session_id: str
    transcript_path: str
    cwd: str
    permission_mode: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None


# =============================================================================
# Specific Hook Input Types
# =============================================================================


@dataclass
class PreToolUseHookInput(BaseHookInput):
    """Input for PreToolUse hooks (fired before a tool executes)."""

    hook_event_name: Literal["PreToolUse"] = "PreToolUse"
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    tool_use_id: str = ""


@dataclass
class PostToolUseHookInput(BaseHookInput):
    """Input for PostToolUse hooks (fired after a tool succeeds)."""

    hook_event_name: Literal["PostToolUse"] = "PostToolUse"
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    tool_response: Any = None
    tool_use_id: str = ""


@dataclass
class PostToolUseFailureHookInput(BaseHookInput):
    """Input for PostToolUseFailure hooks (fired after a tool fails)."""

    hook_event_name: Literal["PostToolUseFailure"] = "PostToolUseFailure"
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    tool_use_id: str = ""
    error: str = ""
    is_interrupt: bool = False


@dataclass
class PermissionDeniedHookInput(BaseHookInput):
    """Input for PermissionDenied hooks."""

    hook_event_name: Literal["PermissionDenied"] = "PermissionDenied"
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    tool_use_id: str = ""
    reason: str = ""


@dataclass
class NotificationHookInput(BaseHookInput):
    """Input for Notification hooks."""

    hook_event_name: Literal["Notification"] = "Notification"
    message: str = ""
    title: str | None = None
    notification_type: str = ""


@dataclass
class UserPromptSubmitHookInput(BaseHookInput):
    """Input for UserPromptSubmit hooks (fired when user submits a prompt)."""

    hook_event_name: Literal["UserPromptSubmit"] = "UserPromptSubmit"
    prompt: str = ""


@dataclass
class SessionStartHookInput(BaseHookInput):
    """Input for SessionStart hooks."""

    hook_event_name: Literal["SessionStart"] = "SessionStart"
    source: Literal["startup", "resume", "clear", "compact"] = "startup"
    agent_type: str | None = None
    model: str | None = None


@dataclass
class SetupHookInput(BaseHookInput):
    """Input for Setup hooks."""

    hook_event_name: Literal["Setup"] = "Setup"
    trigger: Literal["init", "maintenance"] = "init"


@dataclass
class StopHookInput(BaseHookInput):
    """Input for Stop hooks (fired when session stops)."""

    hook_event_name: Literal["Stop"] = "Stop"
    stop_hook_active: bool = False
    last_assistant_message: str | None = None


@dataclass
class StopFailureHookInput(BaseHookInput):
    """Input for StopFailure hooks."""

    hook_event_name: Literal["StopFailure"] = "StopFailure"
    error: str = ""
    error_details: str | None = None
    last_assistant_message: str | None = None


@dataclass
class SubagentStartHookInput(BaseHookInput):
    """Input for SubagentStart hooks."""

    hook_event_name: Literal["SubagentStart"] = "SubagentStart"
    agent_id: str = ""
    agent_type: str = ""


@dataclass
class SubagentStopHookInput(BaseHookInput):
    """Input for SubagentStop hooks."""

    hook_event_name: Literal["SubagentStop"] = "SubagentStop"
    stop_hook_active: bool = False
    agent_id: str = ""
    agent_transcript_path: str = ""
    agent_type: str = ""
    last_assistant_message: str | None = None


@dataclass
class PreCompactHookInput(BaseHookInput):
    """Input for PreCompact hooks."""

    hook_event_name: Literal["PreCompact"] = "PreCompact"
    trigger: Literal["manual", "auto"] = "manual"
    custom_instructions: str | None = None


@dataclass
class PostCompactHookInput(BaseHookInput):
    """Input for PostCompact hooks."""

    hook_event_name: Literal["PostCompact"] = "PostCompact"
    trigger: Literal["manual", "auto"] = "manual"
    compact_summary: str = ""


@dataclass
class PermissionRequestHookInput(BaseHookInput):
    """Input for PermissionRequest hooks."""

    hook_event_name: Literal["PermissionRequest"] = "PermissionRequest"
    tool_name: str = ""
    tool_input: dict[str, Any] | None = None
    permission_suggestions: list[dict[str, Any]] | None = None


@dataclass
class TeammateIdleHookInput(BaseHookInput):
    """Input for TeammateIdle hooks."""

    hook_event_name: Literal["TeammateIdle"] = "TeammateIdle"
    teammate_name: str = ""
    team_name: str = ""


@dataclass
class TaskCreatedHookInput(BaseHookInput):
    """Input for TaskCreated hooks."""

    hook_event_name: Literal["TaskCreated"] = "TaskCreated"
    task_id: str = ""
    task_subject: str = ""
    task_description: str | None = None
    teammate_name: str | None = None
    team_name: str | None = None


@dataclass
class TaskCompletedHookInput(BaseHookInput):
    """Input for TaskCompleted hooks."""

    hook_event_name: Literal["TaskCompleted"] = "TaskCompleted"
    task_id: str = ""
    task_subject: str = ""
    task_description: str | None = None
    teammate_name: str | None = None
    team_name: str | None = None


@dataclass
class ElicitationHookInput(BaseHookInput):
    """Input for Elicitation hooks (MCP user input requests)."""

    hook_event_name: Literal["Elicitation"] = "Elicitation"
    mcp_server_name: str = ""
    message: str = ""
    mode: Literal["form", "url"] | None = None
    url: str | None = None
    elicitation_id: str | None = None
    requested_schema: dict[str, Any] | None = None


@dataclass
class ElicitationResultHookInput(BaseHookInput):
    """Input for ElicitationResult hooks."""

    hook_event_name: Literal["ElicitationResult"] = "ElicitationResult"
    mcp_server_name: str = ""
    elicitation_id: str | None = None
    mode: Literal["form", "url"] | None = None
    action: Literal["accept", "decline", "cancel"] = "cancel"
    content: dict[str, Any] | None = None


@dataclass
class ConfigChangeHookInput(BaseHookInput):
    """Input for ConfigChange hooks."""

    hook_event_name: Literal["ConfigChange"] = "ConfigChange"
    source: Literal[
        "user_settings",
        "project_settings",
        "local_settings",
        "policy_settings",
        "skills",
    ] = "user_settings"
    file_path: str | None = None


@dataclass
class InstructionsLoadedHookInput(BaseHookInput):
    """Input for InstructionsLoaded hooks."""

    hook_event_name: Literal["InstructionsLoaded"] = "InstructionsLoaded"
    file_path: str = ""
    memory_type: Literal["User", "Project", "Local", "Managed"] = "Project"
    load_reason: Literal[
        "session_start",
        "nested_traversal",
        "path_glob_match",
        "include",
        "compact",
    ] = "session_start"
    globs: list[str] | None = None
    trigger_file_path: str | None = None
    parent_file_path: str | None = None


@dataclass
class WorktreeCreateHookInput(BaseHookInput):
    """Input for WorktreeCreate hooks."""

    hook_event_name: Literal["WorktreeCreate"] = "WorktreeCreate"
    name: str = ""


@dataclass
class WorktreeRemoveHookInput(BaseHookInput):
    """Input for WorktreeRemove hooks."""

    hook_event_name: Literal["WorktreeRemove"] = "WorktreeRemove"
    worktree_path: str = ""


@dataclass
class CwdChangedHookInput(BaseHookInput):
    """Input for CwdChanged hooks."""

    hook_event_name: Literal["CwdChanged"] = "CwdChanged"
    old_cwd: str = ""
    new_cwd: str = ""


@dataclass
class FileChangedHookInput(BaseHookInput):
    """Input for FileChanged hooks."""

    hook_event_name: Literal["FileChanged"] = "FileChanged"
    file_path: str = ""
    event: Literal["change", "add", "unlink"] = "change"


@dataclass
class SessionEndHookInput(BaseHookInput):
    """Input for SessionEnd hooks."""

    hook_event_name: Literal["SessionEnd"] = "SessionEnd"
    reason: Literal[
        "clear", "resume", "logout", "prompt_input_exit", "other", "bypass_permissions_disabled"
    ] = "other"


# Union of all hook input types
HookInput = (
    PreToolUseHookInput
    | PostToolUseHookInput
    | PostToolUseFailureHookInput
    | PermissionDeniedHookInput
    | NotificationHookInput
    | UserPromptSubmitHookInput
    | SessionStartHookInput
    | SessionEndHookInput
    | StopHookInput
    | StopFailureHookInput
    | SubagentStartHookInput
    | SubagentStopHookInput
    | PreCompactHookInput
    | PostCompactHookInput
    | PermissionRequestHookInput
    | SetupHookInput
    | TeammateIdleHookInput
    | TaskCreatedHookInput
    | TaskCompletedHookInput
    | ElicitationHookInput
    | ElicitationResultHookInput
    | ConfigChangeHookInput
    | InstructionsLoadedHookInput
    | WorktreeCreateHookInput
    | WorktreeRemoveHookInput
    | CwdChangedHookInput
    | FileChangedHookInput
)


# =============================================================================
# Hook Output / Response Types
# =============================================================================


@dataclass
class AsyncHookJSONOutput:
    """Response indicating the hook will run asynchronously."""

    is_async: Literal[True] = True
    asyncTimeout: int | None = None


@dataclass
class SyncHookJSONOutput:
    """Response from a synchronous hook."""

    continue_: bool | None = field(default=None, repr=False)
    suppressOutput: bool | None = None
    stopReason: str | None = None
    decision: Literal["approve", "block"] | None = None
    reason: str | None = None
    systemMessage: str | None = None
    hookSpecificOutput: dict[str, Any] | None = None

    # Python 3.10+ compatibility for field names with underscores
    def __getattr__(self, name: str) -> Any:
        if name == "continue":
            return self.continue_
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


HookJSONOutput = AsyncHookJSONOutput | SyncHookJSONOutput


# =============================================================================
# Hook Command Types (settings configuration)
# =============================================================================


@dataclass
class BashCommandHook:
    """Shell command hook configuration."""

    type: Literal["command"] = "command"
    command: str = ""
    if_: str | None = field(default=None, repr=False)
    shell: Literal["bash", "powershell"] | None = None
    timeout: int | None = None
    statusMessage: str | None = None
    once: bool = False
    async_: bool = field(default=False, repr=False)
    asyncRewake: bool = False

    def __getattr__(self, name: str) -> Any:
        if name == "if":
            return self.if_
        if name == "async":
            return self.async_
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


@dataclass
class PromptHook:
    """LLM prompt hook configuration."""

    type: Literal["prompt"] = "prompt"
    prompt: str = ""
    if_: str | None = field(default=None, repr=False)
    timeout: int | None = None
    model: str | None = None
    statusMessage: str | None = None
    once: bool = False

    def __getattr__(self, name: str) -> Any:
        if name == "if":
            return self.if_
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


@dataclass
class AgentHook:
    """Agentic verifier hook configuration."""

    type: Literal["agent"] = "agent"
    prompt: str = ""
    if_: str | None = field(default=None, repr=False)
    timeout: int | None = None
    model: str | None = None
    statusMessage: str | None = None
    once: bool = False

    def __getattr__(self, name: str) -> Any:
        if name == "if":
            return self.if_
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


@dataclass
class HttpHook:
    """HTTP POST hook configuration."""

    type: Literal["http"] = "http"
    url: str = ""
    if_: str | None = field(default=None, repr=False)
    timeout: int | None = None
    headers: dict[str, str] | None = None
    allowedEnvVars: list[str] | None = None
    statusMessage: str | None = None
    once: bool = False

    def __getattr__(self, name: str) -> Any:
        if name == "if":
            return self.if_
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


HookCommand = BashCommandHook | PromptHook | AgentHook | HttpHook


# =============================================================================
# Hook Matcher and Settings
# =============================================================================


@dataclass
class HookMatcher:
    """Matcher configuration with a list of hooks to execute."""

    matcher: str | None = None
    hooks: list[HookCommand] = field(default_factory=list)


# Type alias: hooks settings is a partial dict of event -> matchers
HooksSettings = dict[str, list[HookMatcher]]


# =============================================================================
# Hook Callback (runtime execution)
# =============================================================================


@dataclass
class HookCallbackContext:
    """Context passed to callback hooks for state access."""

    get_app_state: Callable[[], dict[str, Any]]
    update_attribution_state: Callable[
        [Callable[[dict[str, Any]], dict[str, Any]]], None
    ]


@dataclass
class HookCallback:
    """A callback-based hook (as opposed to command/prompt/agent/http)."""

    callback: Callable[
        [dict[str, Any], str | None, Any, int | None, HookCallbackContext | None],
        Any,
    ]
    timeout: int | None = None
    internal: bool = False


@dataclass
class HookCallbackMatcher:
    """Matcher configuration for callback hooks."""

    matcher: str | None = None
    hooks: list[HookCallback] = field(default_factory=list)
    plugin_name: str | None = None


# =============================================================================
# Hook Result Types (internal execution results)
# =============================================================================


@dataclass
class HookBlockingError:
    """Error that blocks hook execution continuation."""

    blockingError: str = ""
    command: str = ""


@dataclass
class PermissionRequestAllowResult:
    """Allow result from a PermissionRequest hook."""

    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = field(default=None, repr=False)
    updated_permissions: list[dict[str, Any]] | None = None

    def __getattr__(self, name: str) -> Any:
        if name == "updatedInput":
            return self.updated_input
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


@dataclass
class PermissionRequestDenyResult:
    """Deny result from a PermissionRequest hook."""

    behavior: Literal["deny"] = "deny"
    message: str | None = None
    interrupt: bool = False


PermissionRequestResult = PermissionRequestAllowResult | PermissionRequestDenyResult


@dataclass
class HookResult:
    """Result of a single hook execution."""

    outcome: Literal[
        "success", "blocking", "non_blocking_error", "cancelled"
    ] = "success"
    message: dict[str, Any] | None = None
    system_message: dict[str, Any] | None = field(default=None, repr=False)
    blocking_error: HookBlockingError | None = field(default=None, repr=False)
    prevent_continuation: bool = False
    stop_reason: str | None = None
    permission_behavior: PermissionBehavior | None = None
    hook_permission_decision_reason: str | None = None
    additional_context: str | None = None
    initial_user_message: str | None = None
    updated_input: dict[str, Any] | None = field(default=None, repr=False)
    updated_mcp_tool_output: Any = None
    permission_request_result: PermissionRequestResult | None = None
    retry: bool = False

    def __getattr__(self, name: str) -> Any:
        if name == "systemMessage":
            return self.system_message
        if name == "blockingError":
            return self.blocking_error
        if name == "preventContinuation":
            return self.prevent_continuation
        if name == "hookPermissionDecisionReason":
            return self.hook_permission_decision_reason
        if name == "initialUserMessage":
            return self.initial_user_message
        if name == "updatedInput":
            return self.updated_input
        if name == "updatedMCPToolOutput":
            return self.updated_mcp_tool_output
        if name == "permissionRequestResult":
            return self.permission_request_result
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


@dataclass
class AggregatedHookResult:
    """Aggregated result from multiple hook executions."""

    outcome: Literal[
        "success", "blocking", "non_blocking_error", "cancelled"
    ] = "success"
    message: dict[str, Any] | None = None
    blocking_errors: list[HookBlockingError] | None = None
    prevent_continuation: bool = False
    stop_reason: str | None = None
    hook_permission_decision_reason: str | None = None
    permission_behavior: PermissionBehavior | None = None
    additional_contexts: list[str] | None = None
    initial_user_message: str | None = None
    updated_input: dict[str, Any] | None = field(default=None, repr=False)
    updated_mcp_tool_output: Any = None
    permission_request_result: PermissionRequestResult | None = None
    retry: bool = False

    def __getattr__(self, name: str) -> Any:
        if name == "blockingErrors":
            return self.blocking_errors
        if name == "preventContinuation":
            return self.prevent_continuation
        if name == "hookPermissionDecisionReason":
            return self.hook_permission_decision_reason
        if name == "additionalContexts":
            return self.additional_contexts
        if name == "initialUserMessage":
            return self.initial_user_message
        if name == "updatedInput":
            return self.updated_input
        if name == "updatedMCPToolOutput":
            return self.updated_mcp_tool_output
        if name == "permissionRequestResult":
            return self.permission_request_result
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


# =============================================================================
# Hook Progress (for status reporting)
# =============================================================================


@dataclass
class HookProgress:
    """Progress event for hook execution (for UI/status reporting)."""

    type: Literal["hook_progress"] = "hook_progress"
    hook_event: str = ""
    hook_name: str = ""
    command: str = ""
    prompt_text: str | None = None
    status_message: str | None = None


# =============================================================================
# Prompt Elicitation Types
# =============================================================================


@dataclass
class PromptRequestOption:
    """Option in a prompt elicitation request."""

    key: str = ""
    label: str = ""
    description: str | None = None


@dataclass
class PromptRequest:
    """Prompt elicitation request (shown to user for selection)."""

    prompt: str = ""  # Request ID
    message: str = ""
    options: list[PromptRequestOption] | None = None


@dataclass
class PromptResponse:
    """User's response to a prompt elicitation request."""

    prompt_response: str = ""  # Request ID
    selected: str = ""


# =============================================================================
# Type Guards
# =============================================================================


def is_sync_hook_output(obj: dict[str, Any]) -> bool:
    """Check if a hook output dict is a synchronous response."""
    return obj.get("is_async") is not True


def is_async_hook_output(obj: dict[str, Any]) -> bool:
    """Check if a hook output dict is an async response."""
    return obj.get("is_async") is True
