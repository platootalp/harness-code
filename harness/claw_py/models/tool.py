"""
Tool type definitions and base class for Claude Code tools.

This module defines the core tool infrastructure including:
- ToolDefinition: Schema and metadata for a tool
- ToolResult: Wrapper for tool execution results
- ToolUseContext: Execution context passed to tools
- BaseTool: Abstract base class for all tools
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    TypeVar,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID



# =============================================================================
# Core Type Aliases
# =============================================================================

AnyObject = dict[str, Any]

T = TypeVar("T")
P = TypeVar("P")


# =============================================================================
# Tool Input JSON Schema
# =============================================================================

ToolInputJSONSchema = dict[str, Any]


# =============================================================================
# Validation Result
# =============================================================================

ValidationResult = Literal[True] | tuple[Literal[False], str, int]


# =============================================================================
# Tool Permission Context
# =============================================================================

@dataclass(frozen=True)
class ToolPermissionContext:
    """Context needed for permission checking during tool execution."""

    mode: str = "default"
    additional_working_directories: Mapping[str, dict[str, Any]] = field(
        default_factory=dict
    )
    always_allow_rules: dict[str, list[str]] = field(default_factory=dict)
    always_deny_rules: dict[str, list[str]] = field(default_factory=dict)
    always_ask_rules: dict[str, list[str]] = field(default_factory=dict)
    is_bypass_permissions_mode_available: bool = False
    is_auto_mode_available: bool | None = None
    stripped_dangerous_rules: dict[str, list[str]] | None = None
    should_avoid_permission_prompts: bool | None = None
    await_automated_checks_before_dialog: bool | None = None
    pre_plan_mode: str | None = None


def get_empty_tool_permission_context() -> ToolPermissionContext:
    """Factory for an empty permission context."""
    return ToolPermissionContext()


# =============================================================================
# Tool Progress Types
# =============================================================================

@dataclass
class ToolProgress(Generic[P]):
    """Progress event during tool execution."""

    tool_use_id: str
    data: P


ToolCallProgress = Callable[[ToolProgress[Any]], None]


# =============================================================================
# Compact Progress Events
# =============================================================================

CompactProgressEvent = (
    dict[Literal["type"], Literal["hooks_start"]]
    | dict[Literal["type"], Literal["compact_start"]]
    | dict[Literal["type"], Literal["compact_end"]]
)


# =============================================================================
# Tool Use Context (simplified)
# =============================================================================

@dataclass
class ToolUseContext:
    """Context passed during tool execution.

    Contains all the state and callbacks needed by tools to execute
    and report progress.
    """

    # Execution control
    abort_controller: asyncio.AbstractEventLoop

    # Tool options
    commands: list[Any] = field(default_factory=list)
    debug: bool = False
    main_loop_model: str = ""
    tools: list[Any] = field(default_factory=list)
    verbose: bool = False
    thinking_config: dict[str, Any] = field(default_factory=dict)
    mcp_clients: list[Any] = field(default_factory=list)
    mcp_resources: dict[str, list[Any]] = field(default_factory=dict)
    is_non_interactive_session: bool = False
    agent_definitions: dict[str, Any] = field(default_factory=dict)
    max_budget_usd: float | None = None
    custom_system_prompt: str | None = None
    append_system_prompt: str | None = None
    query_source: str | None = None

    # State access
    messages: list[Any] = field(default_factory=list)

    # Callbacks
    read_file_state: Any = None
    get_app_state: Callable[[], Any] | None = None
    set_app_state: Callable[[Callable[[Any], Any]], None] | None = None
    set_app_state_for_tasks: Callable[[Callable[[Any], Any]], None] | None = None

    # UI callbacks
    set_tool_jsx: Callable[[dict[str, Any] | None], None] | None = None
    add_notification: Callable[[dict[str, Any]], None] | None = None
    append_system_message: Callable[[Any], None] | None = None
    send_os_notification: Callable[[dict[str, Any]], None] | None = None

    # Tool tracking
    set_in_progress_tool_use_ids: Callable[[Callable[[set[str]], set[str]]], None] | None = None
    set_has_interruptible_tool_in_progress: Callable[[bool], None] | None = None
    set_response_length: Callable[[Callable[[int], int]], None] | None = None
    set_stream_mode: Callable[[str], None] | None = None
    set_sdk_status: Callable[[str], None] | None = None

    # File state
    update_file_history_state: Callable[[Callable[[dict[str, Any]], dict[str, Any]]], None] | None = None
    update_attribution_state: Callable[[Callable[[dict[str, Any]], dict[str, Any]]], None] | None = None

    # Session/Agent IDs
    set_conversation_id: Callable[[UUID], None] | None = None
    agent_id: str | None = None
    agent_type: str | None = None

    # Tool execution options
    require_can_use_tool: bool = False
    preserve_tool_use_results: bool = False
    user_modified: bool = False
    tool_use_id: str | None = None

    # Limits
    file_reading_limits: dict[str, Any] | None = None
    glob_limits: dict[str, Any] | None = None

    # Decision tracking
    tool_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    query_tracking: dict[str, Any] | None = None

    # Memory/MCP tracking
    nested_memory_attachment_triggers: set[str] = field(default_factory=set)
    loaded_nested_memory_paths: set[str] | None = None
    dynamic_skill_dir_triggers: set[str] | None = None
    discovered_skill_names: set[str] | None = None

    # Elicitation
    handle_elicitation: Callable[..., Awaitable[Any]] | None = None
    request_prompt: Callable[[str, str | None], Callable[..., Awaitable[Any]]] | None = None

    # Hook callbacks
    on_compact_progress: Callable[[CompactProgressEvent], None] | None = None
    push_api_metrics_entry: Callable[[float], None] | None = None
    open_message_selector: Callable[[], None] | None = None

    # Permission context
    tool_permission_context: ToolPermissionContext = field(
        default_factory=get_empty_tool_permission_context
    )

    # Progress tracking
    refresh_tools: Callable[[], list[Any]] | None = None

    # Debug/experimental
    critical_system_reminder: str | None = None


# =============================================================================
# Tool Result
# =============================================================================

@dataclass
class ToolResult(Generic[T]):
    """Result wrapper for tool execution.

    Attributes:
        data: The actual result data from the tool.
        new_messages: Optional new messages to append to the conversation.
        context_modifier: Optional function to modify the tool use context.
        mcp_meta: MCP protocol metadata for SDK consumers.
    """

    data: T
    new_messages: list[Any] | None = None
    context_modifier: Callable[[ToolUseContext], ToolUseContext] | None = None
    mcp_meta: dict[str, Any] | None = None


# =============================================================================
# Permission Result
# =============================================================================

@dataclass
class PermissionAllowResult:
    """Permission was granted."""

    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    user_modified: bool | None = None
    decision_reason: dict[str, Any] | None = None
    tool_use_id: str | None = None
    accept_feedback: str | None = None
    content_blocks: list[Any] | None = None


@dataclass
class PermissionAskResult:
    """User should be prompted for permission."""

    behavior: Literal["ask"] = "ask"
    message: str = ""
    updated_input: dict[str, Any] | None = None
    decision_reason: dict[str, Any] | None = None
    suggestions: list[Any] | None = None
    blocked_path: str | None = None
    metadata: dict[str, Any] | None = None
    is_bash_security_check_for_misparsing: bool | None = None
    pending_classifier_check: dict[str, Any] | None = None
    content_blocks: list[Any] | None = None


@dataclass
class PermissionDenyResult:
    """Permission was denied."""

    behavior: Literal["deny"] = "deny"
    message: str = ""
    decision_reason: dict[str, Any] = field(default_factory=dict)
    tool_use_id: str | None = None


@dataclass
class PermissionPassthroughResult:
    """Permission decision passed through to hook/system."""

    behavior: Literal["passthrough"] = "passthrough"
    message: str = ""
    decision_reason: dict[str, Any] | None = None
    suggestions: list[Any] | None = None
    blocked_path: str | None = None
    pending_classifier_check: dict[str, Any] | None = None


PermissionResult = (
    PermissionAllowResult
    | PermissionAskResult
    | PermissionDenyResult
    | PermissionPassthroughResult
)


# =============================================================================
# Helper Functions
# =============================================================================

def tool_matches_name(tool: Any, name: str) -> bool:
    """Check if a tool matches the given name or an alias.

    Args:
        tool: Tool object with name and optionally aliases.
        name: Name to match against.

    Returns:
        True if the tool's name or any alias matches.
    """
    if tool.name == name:
        return True
    aliases = getattr(tool, "aliases", None)
    if aliases is not None:
        return name in aliases
    return False


def find_tool_by_name(tools: Sequence[Any], name: str) -> Any | None:
    """Find a tool by name or alias from a list of tools.

    Args:
        tools: Sequence of tool objects to search.
        name: Name or alias to find.

    Returns:
        The matching tool or None if not found.
    """
    for tool in tools:
        if tool_matches_name(tool, name):
            return tool
    return None


def filter_tool_progress_messages(
    progress_messages: Sequence[Any],
) -> list[Any]:
    """Filter progress messages to exclude hook progress.

    Args:
        progress_messages: List of progress messages.

    Returns:
        Messages that are not hook_progress type.
    """
    result = []
    for msg in progress_messages:
        data = getattr(msg, "data", None)
        if data is not None and data.get("type") != "hook_progress":
            result.append(msg)
    return result


# =============================================================================
# Progress Types (simplified)
# =============================================================================

# Tool progress data types
@dataclass
class BashProgress:
    type: Literal["bash"] = "bash"
    command: str = ""
    working_directory: str | None = None
    exit_code: int | None = None
    killed: bool = False


@dataclass
class MCPToolProgress:
    type: Literal["mcp"] = "mcp"
    server_name: str = ""
    tool_name: str = ""
    status: str = ""


@dataclass
class WebSearchProgress:
    type: Literal["websearch"] = "websearch"
    query: str = ""


@dataclass
class TaskOutputProgress:
    type: Literal["task_output"] = "task_output"
    task_id: str = ""
    status: str = ""


@dataclass
class REPLToolProgress:
    type: Literal["repl"] = "repl"
    command: str = ""


@dataclass
class SkillToolProgress:
    type: Literal["skill"] = "skill"
    skill_name: str = ""


@dataclass
class AgentToolProgress:
    type: Literal["agent"] = "agent"
    agent_id: str = ""
    status: str = ""


ToolProgressData = (
    BashProgress
    | MCPToolProgress
    | WebSearchProgress
    | TaskOutputProgress
    | REPLToolProgress
    | SkillToolProgress
    | AgentToolProgress
    | dict[str, Any]
)


# =============================================================================
# CanUseTool Function Type
# =============================================================================

CanUseToolFn = Callable[..., Awaitable[PermissionResult]]


# =============================================================================
# Base Tool Abstract Class
# =============================================================================

@dataclass
class BaseTool(ABC):
    """Abstract base class for all Claude Code tools.

    Tools provide capabilities that the model can invoke to accomplish
    tasks. Each tool has an input schema, execution logic, and metadata.

    Subclasses must implement:
    - name: The tool's unique identifier
    - input_schema: JSON Schema for the tool's input parameters
    - call: The main execution logic
    - description: Human-readable description of the tool
    - user_facing_name: How the tool appears in the UI
    """

    # Metadata - use init=False so child classes can override in their __init__
    aliases: list[str] | None = field(default=None, init=False)
    search_hint: str | None = field(default=None, init=False)
    should_defer: bool = field(default=False, init=False)
    always_load: bool = field(default=False, init=False)
    max_result_size_chars: int = field(default=100_000, init=False)
    strict: bool = field(default=False, init=False)

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool's unique identifier."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> ToolInputJSONSchema:
        """JSON Schema for the tool's input parameters."""
        ...

    @property
    def output_schema(self) -> dict[str, Any] | None:
        """JSON Schema for the tool's output (optional)."""
        return None

    @abstractmethod
    async def call(
        self,
        args: AnyObject,
        context: ToolUseContext,
        can_use_tool: CanUseToolFn,
        parent_message: Any,
        on_progress: ToolCallProgress | None = None,
    ) -> ToolResult[Any]:
        """Execute the tool with the given arguments.

        Args:
            args: Tool input arguments validated against input_schema.
            context: Execution context with state and callbacks.
            can_use_tool: Function to check if tool can execute.
            parent_message: The assistant message that triggered this call.
            on_progress: Optional callback for progress updates.

        Returns:
            ToolResult with the execution result.
        """
        ...

    async def description(
        self,
        input: Any,
        options: dict[str, Any],
    ) -> str:
        """Get a human-readable description of the tool.

        Args:
            input: The input arguments (may be partial).
            options: Description options including:
                - is_non_interactive_session: bool
                - tool_permission_context: ToolPermissionContext
                - tools: list of available tools

        Returns:
            Human-readable description string.
        """
        return f"Tool: {self.name}"

    async def prompt(
        self,
        options: dict[str, Any],
    ) -> str:
        """Get the system prompt for this tool.

        Args:
            options: Prompt options including:
                - get_tool_permission_context: callable
                - tools: available tools
                - agents: available agents
                - allowed_agent_types: optional list

        Returns:
            System prompt string for this tool.
        """
        return ""

    def user_facing_name(self, input: Any | None = None) -> str:
        """Get the display name for the tool in the UI.

        Args:
            input: Optional partial input for context-dependent naming.

        Returns:
            Display name string.
        """
        return self.name

    def is_enabled(self) -> bool:
        """Check if the tool is currently enabled.

        Returns:
            True if the tool can be used.
        """
        return True

    def is_concurrency_safe(self, input: Any) -> bool:
        """Check if this tool can safely run concurrently with other tools.

        Args:
            input: The tool input arguments.

        Returns:
            True if safe to run concurrently.
        """
        return False

    def is_read_only(self, input: Any) -> bool:
        """Check if this tool only reads data without modifications.

        Args:
            input: The tool input arguments.

        Returns:
            True if the tool only reads.
        """
        return False

    def is_destructive(self, input: Any) -> bool:
        """Check if this tool performs irreversible operations.

        Args:
            input: The tool input arguments.

        Returns:
            True if the tool is destructive.
        """
        return False

    async def check_permissions(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> PermissionResult:
        """Check if the user has permission to run this tool.

        Args:
            input: The tool input arguments.
            context: Execution context.

        Returns:
            Permission result indicating allow/ask/deny.
        """
        return PermissionAllowResult()

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution.

        Args:
            input: The tool input arguments.
            context: Execution context.

        Returns:
            ValidationResult - True if valid, or (False, message, error_code).
        """
        return True

    def get_path(self, input: Any) -> str | None:
        """Get the file path this tool operates on (if any).

        Args:
            input: The tool input arguments.

        Returns:
            File path or None.
        """
        return None

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        """Check if this is a search/read operation for UI display.

        Args:
            input: The tool input arguments.

        Returns:
            Dict with is_search, is_read, and optional is_list flags.
        """
        return {"is_search": False, "is_read": False}

    def is_open_world(self, input: Any) -> bool:
        """Check if this tool accesses external resources.

        Args:
            input: The tool input arguments.

        Returns:
            True if accessing external resources.
        """
        return False

    def requires_user_interaction(self) -> bool:
        """Check if this tool requires user interaction.

        Returns:
            True if user interaction is needed.
        """
        return False

    def interrupt_behavior(self) -> Literal["cancel", "block"]:
        """What happens when user submits while tool is running.

        Returns:
            'cancel' to stop and discard, 'block' to queue.
        """
        return "block"

    def to_auto_classifier_input(self, input: Any) -> Any:
        """Get input for the auto-mode security classifier.

        Args:
            input: The tool input arguments.

        Returns:
            Serializable input for classifier.
        """
        return ""


# =============================================================================
# Tool Definition (for tool builders)
# =============================================================================

ToolDef = dict[str, Any]


# =============================================================================
# Tool Defaults
# =============================================================================

TOOL_DEFAULTS: dict[str, Any] = {
    "is_enabled": lambda: True,
    "is_concurrency_safe": lambda _: False,
    "is_read_only": lambda _: False,
    "is_destructive": lambda _: False,
    "check_permissions": lambda input, _ctx: PermissionAllowResult(updated_input=input),
    "to_auto_classifier_input": lambda _: "",
    "user_facing_name": lambda _: "",
}


def build_tool(tool_def: ToolDef) -> dict[str, Any]:
    """Build a complete tool from a partial definition.

    Fills in safe defaults for commonly-stubbed methods:
    - isEnabled -> True
    - isConcurrencySafe -> False
    - isReadOnly -> False
    - isDestructive -> False
    - checkPermissions -> allow
    - toAutoClassifierInput -> ''
    - userFacingName -> name

    Args:
        tool_def: Tool definition with at minimum 'name'.

    Returns:
        Complete tool with defaults filled in.
    """
    name = tool_def.get("name", "")
    return {
        **TOOL_DEFAULTS,
        "user_facing_name": lambda _input=None, _n=name: _n,
        **tool_def,
    }
