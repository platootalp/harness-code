"""
Permission system types, constants, and utilities.

Provides the core permission infrastructure including:
- PermissionMode: Execution modes (default, plan, acceptEdits, bypassPermissions, etc.)
- PermissionBehavior: Rule behaviors (allow, deny, ask)
- PermissionRule: Rule structure with source and behavior
- PermissionDecision/Result: Tool execution permission outcomes
- ToolPermissionContext: Context passed to tools for permission checking
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypedDict,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Permission Modes
# =============================================================================


EXTERNAL_PERMISSION_MODES: tuple[str, ...] = (
    "acceptEdits",
    "bypassPermissions",
    "default",
    "dontAsk",
    "plan",
)

ExternalPermissionMode = Literal[
    "acceptEdits", "bypassPermissions", "default", "dontAsk", "plan"
]

InternalPermissionMode = ExternalPermissionMode | Literal["auto"] | Literal["bubble"]
PermissionMode = InternalPermissionMode

INTERNAL_PERMISSION_MODES: tuple[str, ...] = (
    "acceptEdits",
    "bypassPermissions",
    "default",
    "dontAsk",
    "plan",
    "auto",
    "bubble",
)
PERMISSION_MODES = INTERNAL_PERMISSION_MODES


# =============================================================================
# Permission Behaviors
# =============================================================================


PermissionBehavior = Literal["allow", "deny", "ask"]


# =============================================================================
# Permission Rules
# =============================================================================


PermissionRuleSource = Literal[
    "userSettings",
    "projectSettings",
    "localSettings",
    "flagSettings",
    "policySettings",
    "cliArg",
    "command",
    "session",
]


@dataclass(frozen=True)
class PermissionRuleValue:
    """The value of a permission rule - specifies which tool and optional content."""

    tool_name: str
    rule_content: str | None = None


@dataclass(frozen=True)
class PermissionRule:
    """A permission rule with its source and behavior."""

    source: PermissionRuleSource
    rule_behavior: PermissionBehavior
    rule_value: PermissionRuleValue


# =============================================================================
# Permission Updates
# =============================================================================


PermissionUpdateDestination = Literal[
    "userSettings", "projectSettings", "localSettings", "session", "cliArg"
]


@dataclass(frozen=True)
class PermissionUpdateAddRules:
    """Add permission rules to a destination."""

    type: Literal["addRules"] = "addRules"
    destination: PermissionUpdateDestination = "userSettings"
    rules: tuple[PermissionRuleValue, ...] = field(default_factory=tuple)
    behavior: PermissionBehavior = "allow"


@dataclass(frozen=True)
class PermissionUpdateReplaceRules:
    """Replace permission rules in a destination."""

    type: Literal["replaceRules"] = "replaceRules"
    destination: PermissionUpdateDestination = "userSettings"
    rules: tuple[PermissionRuleValue, ...] = field(default_factory=tuple)
    behavior: PermissionBehavior = "allow"


@dataclass(frozen=True)
class PermissionUpdateRemoveRules:
    """Remove permission rules from a destination."""

    type: Literal["removeRules"] = "removeRules"
    destination: PermissionUpdateDestination = "userSettings"
    rules: tuple[PermissionRuleValue, ...] = field(default_factory=tuple)
    behavior: PermissionBehavior = "allow"


@dataclass(frozen=True)
class PermissionUpdateSetMode:
    """Set the permission mode."""

    type: Literal["setMode"] = "setMode"
    destination: PermissionUpdateDestination = "userSettings"
    mode: ExternalPermissionMode = "default"


@dataclass(frozen=True)
class PermissionUpdateAddDirectories:
    """Add directories to permission scope."""

    type: Literal["addDirectories"] = "addDirectories"
    destination: PermissionUpdateDestination = "userSettings"
    directories: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PermissionUpdateRemoveDirectories:
    """Remove directories from permission scope."""

    type: Literal["removeDirectories"] = "removeDirectories"
    destination: PermissionUpdateDestination = "userSettings"
    directories: tuple[str, ...] = field(default_factory=tuple)


PermissionUpdate = (
    PermissionUpdateAddRules
    | PermissionUpdateReplaceRules
    | PermissionUpdateRemoveRules
    | PermissionUpdateSetMode
    | PermissionUpdateAddDirectories
    | PermissionUpdateRemoveDirectories
)


# =============================================================================
# Additional Working Directories
# =============================================================================


WorkingDirectorySource = PermissionRuleSource


@dataclass(frozen=True)
class AdditionalWorkingDirectory:
    """An additional directory included in permission scope."""

    path: str
    source: WorkingDirectorySource = "userSettings"


# =============================================================================
# Permission Decisions & Results
# =============================================================================


class PermissionCommandMetadata(TypedDict, total=False):
    """Minimal command metadata for permission decisions."""

    name: str
    description: str
    # Allow additional properties for forward compatibility
    extra: dict[str, Any]


PermissionMetadata = PermissionCommandMetadata | None


@dataclass
class PermissionAllowDecision:
    """Result when permission is granted."""

    behavior: Literal["allow"] = "allow"
    updated_input: dict[str, Any] | None = None
    user_modified: bool | None = None
    decision_reason: Any = None
    tool_use_id: str | None = None
    accept_feedback: str | None = None
    content_blocks: list[Any] | None = None


@dataclass
class PendingClassifierCheck:
    """Metadata for a pending async classifier check."""

    command: str
    cwd: str
    descriptions: tuple[str, ...]


@dataclass
class PermissionAskDecision:
    """Result when user should be prompted."""

    behavior: Literal["ask"] = "ask"
    message: str = ""
    updated_input: dict[str, Any] | None = None
    decision_reason: Any = None
    suggestions: tuple[Any, ...] | None = None
    blocked_path: str | None = None
    metadata: PermissionMetadata = None
    is_bash_security_check_for_misparsing: bool = False
    pending_classifier_check: PendingClassifierCheck | None = None
    content_blocks: list[Any] | None = None


@dataclass
class PermissionDenyDecision:
    """Result when permission is denied."""

    behavior: Literal["deny"] = "deny"
    message: str = ""
    decision_reason: Any = None
    tool_use_id: str | None = None


@dataclass
class PermissionPassthroughDecision:
    """Result when decision is passed through to hook/system."""

    behavior: Literal["passthrough"] = "passthrough"
    message: str = ""
    decision_reason: Any = None
    suggestions: tuple[Any, ...] | None = None
    blocked_path: str | None = None
    pending_classifier_check: PendingClassifierCheck | None = None


PermissionDecision = PermissionAllowDecision | PermissionAskDecision | PermissionDenyDecision
PermissionResult = PermissionDecision | PermissionPassthroughDecision


# =============================================================================
# Permission Decision Reasons
# =============================================================================


@dataclass(frozen=True)
class DecisionReasonRule:
    """Decision made by a permission rule."""

    rule: Any
    type: Literal["rule"] = "rule"


@dataclass(frozen=True)
class DecisionReasonMode:
    """Decision made by permission mode."""

    mode: PermissionMode
    type: Literal["mode"] = "mode"


@dataclass(frozen=True)
class DecisionReasonSubcommandResults:
    """Decision made from subcommand results."""

    reasons: dict[str, Any]
    type: Literal["subcommandResults"] = "subcommandResults"


@dataclass(frozen=True)
class DecisionReasonPermissionPromptTool:
    """Decision made by permission prompt tool."""

    permission_prompt_tool_name: str
    tool_result: Any
    type: Literal["permissionPromptTool"] = "permissionPromptTool"


@dataclass(frozen=True)
class DecisionReasonHook:
    """Decision made by a hook."""

    hook_name: str
    type: Literal["hook"] = "hook"
    hook_source: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class DecisionReasonAsyncAgent:
    """Decision made by async agent."""

    reason: str
    type: Literal["asyncAgent"] = "asyncAgent"


@dataclass(frozen=True)
class DecisionReasonSandboxOverride:
    """Decision made by sandbox override."""

    reason: Literal["excludedCommand", "dangerouslyDisableSandbox"]
    type: Literal["sandboxOverride"] = "sandboxOverride"


@dataclass(frozen=True)
class DecisionReasonClassifier:
    """Decision made by classifier."""

    classifier: str
    reason: str
    type: Literal["classifier"] = "classifier"


@dataclass(frozen=True)
class DecisionReasonWorkingDir:
    """Decision made by working directory check."""

    reason: str
    type: Literal["workingDir"] = "workingDir"


@dataclass(frozen=True)
class DecisionReasonSafetyCheck:
    """Decision made by safety check."""

    reason: str
    type: Literal["safetyCheck"] = "safetyCheck"
    classifier_approvable: bool = False


@dataclass(frozen=True)
class DecisionReasonOther:
    """Decision made for other reasons."""

    reason: str
    type: Literal["other"] = "other"


PermissionDecisionReason = (
    DecisionReasonRule
    | DecisionReasonMode
    | DecisionReasonSubcommandResults
    | DecisionReasonPermissionPromptTool
    | DecisionReasonHook
    | DecisionReasonAsyncAgent
    | DecisionReasonSandboxOverride
    | DecisionReasonClassifier
    | DecisionReasonWorkingDir
    | DecisionReasonSafetyCheck
    | DecisionReasonOther
)


# =============================================================================
# Tool Permission Context
# =============================================================================


ToolPermissionRulesBySource = dict[PermissionRuleSource, tuple[str, ...]]


@dataclass
class ToolPermissionContext:
    """Context needed for permission checking during tool execution."""

    mode: PermissionMode = "default"
    additional_working_directories: Mapping[str, AdditionalWorkingDirectory] = field(
        default_factory=dict
    )
    always_allow_rules: ToolPermissionRulesBySource = field(default_factory=dict)
    always_deny_rules: ToolPermissionRulesBySource = field(default_factory=dict)
    always_ask_rules: ToolPermissionRulesBySource = field(default_factory=dict)
    is_bypass_permissions_mode_available: bool = False
    stripped_dangerous_rules: ToolPermissionRulesBySource | None = None
    should_avoid_permission_prompts: bool | None = None
    await_automated_checks_before_dialog: bool | None = None
    pre_plan_mode: PermissionMode | None = None


def get_empty_tool_permission_context() -> ToolPermissionContext:
    """Factory for an empty permission context."""
    return ToolPermissionContext()


# =============================================================================
# Permission Checking
# =============================================================================


def _tool_matches_rule(
    tool_name: str,
    rule: PermissionRule,
) -> bool:
    """Check if a tool matches a permission rule.

    Args:
        tool_name: Name of the tool to check.
        rule: The permission rule to match against.

    Returns:
        True if the tool matches the rule.
    """
    rule_tool = rule.rule_value.tool_name
    # Exact match
    if rule_tool == tool_name:
        return True
    # Wildcard: toolName(*:*) matches all tools
    if rule_tool == "*":
        return True
    # MCP pattern: mcp__server1__* matches all tools from server
    if rule_tool.startswith("mcp__") and rule_tool.endswith("__*"):
        server = rule_tool.rsplit("__*", 1)[0]
        return tool_name.startswith(server)
    return False


def _get_allow_rules(
    ctx: ToolPermissionContext,
) -> list[PermissionRule]:
    """Get all allow rules from the permission context.

    Args:
        ctx: The tool permission context.

    Returns:
        List of allow rules from all sources.
    """
    rules: list[PermissionRule] = []
    for source_rules in ctx.always_allow_rules.values():
        for rule_value_str in source_rules:
            # Rules stored as "toolName" or "toolName:content"
            if ":" in rule_value_str:
                tool_name, rule_content = rule_value_str.split(":", 1)
            else:
                tool_name = rule_value_str
                rule_content = None
            rules.append(
                PermissionRule(
                    source="userSettings",
                    rule_behavior="allow",
                    rule_value=PermissionRuleValue(
                        tool_name=tool_name,
                        rule_content=rule_content,
                    ),
                )
            )
    return rules


def _get_deny_rules(
    ctx: ToolPermissionContext,
) -> list[PermissionRule]:
    """Get all deny rules from the permission context.

    Args:
        ctx: The tool permission context.

    Returns:
        List of deny rules from all sources.
    """
    rules: list[PermissionRule] = []
    for source_rules in ctx.always_deny_rules.values():
        for rule_value_str in source_rules:
            if ":" in rule_value_str:
                tool_name, rule_content = rule_value_str.split(":", 1)
            else:
                tool_name = rule_value_str
                rule_content = None
            rules.append(
                PermissionRule(
                    source="userSettings",
                    rule_behavior="deny",
                    rule_value=PermissionRuleValue(
                        tool_name=tool_name,
                        rule_content=rule_content,
                    ),
                )
            )
    return rules


def _get_ask_rules(
    ctx: ToolPermissionContext,
) -> list[PermissionRule]:
    """Get all ask rules from the permission context.

    Args:
        ctx: The tool permission context.

    Returns:
        List of ask rules from all sources.
    """
    rules: list[PermissionRule] = []
    for source_rules in ctx.always_ask_rules.values():
        for rule_value_str in source_rules:
            if ":" in rule_value_str:
                tool_name, rule_content = rule_value_str.split(":", 1)
            else:
                tool_name = rule_value_str
                rule_content = None
            rules.append(
                PermissionRule(
                    source="userSettings",
                    rule_behavior="ask",
                    rule_value=PermissionRuleValue(
                        tool_name=tool_name,
                        rule_content=rule_content,
                    ),
                )
            )
    return rules


def _get_rule_for_tool(
    ctx: ToolPermissionContext,
    tool_name: str,
    rules_getter: Callable[[ToolPermissionContext], list[PermissionRule]],
) -> PermissionRule | None:
    """Find the first matching rule for a tool.

    Args:
        ctx: The tool permission context.
        tool_name: Name of the tool.
        rules_getter: Function to get rules (e.g., _get_allow_rules).

    Returns:
        The matching rule or None.
    """
    rules = rules_getter(ctx)
    for rule in rules:
        if _tool_matches_rule(tool_name, rule):
            return rule
    return None


def _get_deny_rule_for_tool(
    ctx: ToolPermissionContext,
    tool_name: str,
) -> PermissionRule | None:
    """Check if a tool is in the deny rules.

    Args:
        ctx: The tool permission context.
        tool_name: Name of the tool.

    Returns:
        The deny rule if found, None otherwise.
    """
    return _get_rule_for_tool(ctx, tool_name, _get_deny_rules)


def _get_ask_rule_for_tool(
    ctx: ToolPermissionContext,
    tool_name: str,
) -> PermissionRule | None:
    """Check if a tool is in the ask rules.

    Args:
        ctx: The tool permission context.
        tool_name: Name of the tool.

    Returns:
        The ask rule if found, None otherwise.
    """
    return _get_rule_for_tool(ctx, tool_name, _get_ask_rules)


def _tool_always_allowed_rule(
    ctx: ToolPermissionContext,
    tool_name: str,
) -> PermissionRule | None:
    """Check if a tool is in the always allow rules.

    Args:
        ctx: The tool permission context.
        tool_name: Name of the tool.

    Returns:
        The allow rule if found, None otherwise.
    """
    return _get_rule_for_tool(ctx, tool_name, _get_allow_rules)


def check_tool_permission(
    tool_name: str,
    user_context: ToolPermissionContext,
) -> PermissionResult:
    """Check if a tool is allowed to run based on permission context.

    Implements the permission checking pipeline:
    1. Check if tool is in always_deny_rules -> deny
    2. Check if tool is in always_ask_rules -> ask
    3. Check mode-based bypass:
       - bypassPermissions mode -> allow
       - plan mode + isBypassPermissionsModeAvailable -> allow
    4. Check if tool is in always_allow_rules -> allow
    5. Otherwise -> passthrough (caller decides, typically prompts)

    Args:
        tool_name: Name of the tool to check.
        user_context: The tool permission context.

    Returns:
        A PermissionResult indicating allow, ask, deny, or passthrough.
    """
    # 1. Check if the tool is denied by rule
    deny_rule = _get_deny_rule_for_tool(user_context, tool_name)
    if deny_rule:
        return PermissionDenyDecision(
            behavior="deny",
            message=f"Permission to use {tool_name} has been denied.",
            decision_reason=DecisionReasonRule(rule=deny_rule),
        )

    # 2. Check if the tool should always ask for permission
    ask_rule = _get_ask_rule_for_tool(user_context, tool_name)
    if ask_rule:
        return PermissionAskDecision(
            behavior="ask",
            message=f"Permission is required to use {tool_name}.",
            decision_reason=DecisionReasonRule(rule=ask_rule),
        )

    # 3. Check mode-based bypass
    should_bypass = (
        user_context.mode == "bypassPermissions"
        or (
            user_context.mode == "plan"
            and user_context.is_bypass_permissions_mode_available
        )
    )
    if should_bypass:
        return PermissionAllowDecision(
            behavior="allow",
            decision_reason=DecisionReasonMode(mode=user_context.mode),
        )

    # 4. Check if the tool is always allowed
    allow_rule = _tool_always_allowed_rule(user_context, tool_name)
    if allow_rule:
        return PermissionAllowDecision(
            behavior="allow",
            decision_reason=DecisionReasonRule(rule=allow_rule),
        )

    # 5. Default: passthrough (let caller decide - typically prompts user)
    return PermissionPassthroughDecision(
        behavior="passthrough",
        message=f"Permission is required to use {tool_name}.",
    )


# =============================================================================
# Mode Configuration
# =============================================================================


ModeColorKey = Literal["text", "planMode", "permission", "autoAccept", "error", "warning"]


@dataclass(frozen=True)
class PermissionModeConfig:
    """Configuration for a permission mode display."""

    title: str
    short_title: str
    symbol: str
    color: ModeColorKey
    external: ExternalPermissionMode


PERMISSION_MODE_CONFIG: dict[PermissionMode, PermissionModeConfig] = {
    "default": PermissionModeConfig(
        title="Default",
        short_title="Default",
        symbol="",
        color="text",
        external="default",
    ),
    "plan": PermissionModeConfig(
        title="Plan Mode",
        short_title="Plan",
        symbol="⏵⏵",
        color="planMode",
        external="plan",
    ),
    "acceptEdits": PermissionModeConfig(
        title="Accept edits",
        short_title="Accept",
        symbol="⏵⏵",
        color="autoAccept",
        external="acceptEdits",
    ),
    "bypassPermissions": PermissionModeConfig(
        title="Bypass Permissions",
        short_title="Bypass",
        symbol="⏵⏵",
        color="error",
        external="bypassPermissions",
    ),
    "dontAsk": PermissionModeConfig(
        title="Don't Ask",
        short_title="DontAsk",
        symbol="⏵⏵",
        color="error",
        external="dontAsk",
    ),
    "auto": PermissionModeConfig(
        title="Auto mode",
        short_title="Auto",
        symbol="⏵⏵",
        color="warning",
        external="default",
    ),
    "bubble": PermissionModeConfig(
        title="Default",
        short_title="Default",
        symbol="",
        color="text",
        external="default",
    ),
}


def _get_mode_config(mode: PermissionMode) -> PermissionModeConfig:
    """Get the configuration for a permission mode."""
    return PERMISSION_MODE_CONFIG.get(mode, PERMISSION_MODE_CONFIG["default"])


def is_external_permission_mode(mode: PermissionMode) -> bool:
    """Check if a mode is an external permission mode.

    Auto mode is ant-only and excluded from external modes.
    """
    return mode != "auto" and mode != "bubble"


def to_external_permission_mode(mode: PermissionMode) -> ExternalPermissionMode:
    """Convert a permission mode to its external representation."""
    return _get_mode_config(mode).external


def permission_mode_from_string(s: str) -> PermissionMode:
    """Parse a permission mode from a string.

    Args:
        s: String representation of the mode.

    Returns:
        The corresponding PermissionMode, or 'default' if invalid.
    """
    if s in PERMISSION_MODES:
        return s  # type: ignore[return-value]
    return "default"


def permission_mode_title(mode: PermissionMode) -> str:
    """Get the display title for a permission mode."""
    return _get_mode_config(mode).title


def is_default_mode(mode: PermissionMode | None) -> bool:
    """Check if a mode is the default mode (or unset)."""
    return mode == "default" or mode is None


def permission_mode_short_title(mode: PermissionMode) -> str:
    """Get the short display title for a permission mode."""
    return _get_mode_config(mode).short_title


def permission_mode_symbol(mode: PermissionMode) -> str:
    """Get the symbol for a permission mode."""
    return _get_mode_config(mode).symbol


def get_mode_color(mode: PermissionMode) -> ModeColorKey:
    """Get the color key for a permission mode."""
    return _get_mode_config(mode).color


def get_rule_behavior_description(
    behavior: PermissionBehavior,
) -> str:
    """Get the prose description for a rule behavior.

    Args:
        behavior: The permission behavior.

    Returns:
        A human-readable description string.
    """
    if behavior == "allow":
        return "allowed"
    if behavior == "deny":
        return "denied"
    return "asked for confirmation for"


# =============================================================================
# Classifier Types
# =============================================================================


ClassifierConfidence = Literal["high", "medium", "low"]
ClassifierBehavior = Literal["deny", "ask", "allow"]


@dataclass(frozen=True)
class ClassifierResult:
    """Result from a permission classifier."""

    matches: bool
    confidence: ClassifierConfidence
    reason: str
    matched_description: str | None = None


@dataclass(frozen=True)
class ClassifierUsage:
    """Token usage from a classifier API call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class YoloClassifierResult:
    """Result from YOLO classifier evaluation."""

    should_block: bool
    reason: str
    model: str
    thinking: str | None = None
    unavailable: bool = False
    transcript_too_long: bool = False
    usage: ClassifierUsage | None = None
    duration_ms: int | None = None
    prompt_lengths: dict[str, int] | None = None
    error_dump_path: str | None = None
    stage: Literal["fast", "thinking"] | None = None
    stage1_usage: ClassifierUsage | None = None
    stage1_duration_ms: int | None = None
    stage1_request_id: str | None = None
    stage1_msg_id: str | None = None
    stage2_usage: ClassifierUsage | None = None
    stage2_duration_ms: int | None = None
    stage2_request_id: str | None = None
    stage2_msg_id: str | None = None


# =============================================================================
# Permission Explainer Types
# =============================================================================


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class PermissionExplanation:
    """Explanation of why a permission decision was made."""

    risk_level: RiskLevel
    explanation: str
    reasoning: str
    risk: str
