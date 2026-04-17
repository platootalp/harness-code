"""
Hook definitions for the plugin system.

Provides the 25 hook event types and HookDefinition dataclass for
registering plugin hooks.

TypeScript equivalent: src/types/plugin.ts (HookDefinition)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class HookType(StrEnum):
    """Hook execution types."""

    #: Run a shell command
    COMMAND = "command"
    #: LLM prompt evaluation
    PROMPT = "prompt"
    #: HTTP POST request
    HTTP = "http"
    #: Agentic validator
    AGENT = "agent"


class HookEventType(StrEnum):
    """All 25 hook event types supported by the plugin system.

    Organized by category:
    - Tool lifecycle (3)
    - Session lifecycle (3)
    - Agent lifecycle (3)
    - Task lifecycle (2)
    - Compact (2)
    - Permission (2)
    - User interaction (3)
    - Control flow (2)
    - Config (1)
    - Worktree (3)
    """

    # Tool lifecycle
    PreToolUse = "PreToolUse"
    PostToolUse = "PostToolUse"
    PostToolUseFailure = "PostToolUseFailure"

    # Session lifecycle
    SessionStart = "SessionStart"
    SessionEnd = "SessionEnd"
    Setup = "Setup"

    # Agent lifecycle
    SubagentStart = "SubagentStart"
    SubagentStop = "SubagentStop"
    TeammateIdle = "TeammateIdle"

    # Task lifecycle
    TaskCreated = "TaskCreated"
    TaskCompleted = "TaskCompleted"

    # Compact
    PreCompact = "PreCompact"
    PostCompact = "PostCompact"

    # Permission
    PermissionRequest = "PermissionRequest"
    PermissionDenied = "PermissionDenied"

    # User interaction
    UserPromptSubmit = "UserPromptSubmit"
    Notification = "Notification"
    Elicitation = "Elicitation"

    # Control flow
    Stop = "Stop"
    StopFailure = "StopFailure"

    # Config
    ConfigChange = "ConfigChange"

    # Worktree
    WorktreeCreate = "WorktreeCreate"
    WorktreeRemove = "WorktreeRemove"
    InstructionsLoaded = "InstructionsLoaded"


# =============================================================================
# Hook Definition
# =============================================================================


@dataclass
class HookDefinition:
    """A registered hook definition.

    Attributes:
        event: The hook event name (e.g. "PreToolUse", "SessionStart").
        hook_type: How the hook is executed (command, prompt, http, agent).
        command: Shell command to run (for command-type hooks).
        prompt: LLM prompt template (for prompt-type hooks).
        url: URL for HTTP POST (for http-type hooks).
        agent_prompt: Prompt for agentic validation (for agent-type hooks).
        condition: Optional condition expression for filtering.
        timeout: Timeout in seconds (default 30).
        priority: Execution priority (higher runs first). Default 0.
    """

    event: str
    hook_type: HookType = HookType.COMMAND
    command: str | None = None
    prompt: str | None = None
    url: str | None = None
    agent_prompt: str | None = None
    condition: str | None = None
    timeout: int = 30
    priority: int = 0
    _extra: dict[str, Any] = field(default_factory=dict)

    def matches_condition(self, context: dict[str, Any]) -> bool | None:
        """Check if the hook's condition matches the given context.

        Args:
            context: Context data to evaluate the condition against.

        Returns:
            True if condition matches or no condition exists.
            None if the condition cannot be evaluated.
        """
        if not self.condition:
            return True

        # Simple condition evaluation — checks for presence/equality patterns
        # In production this would parse the condition expression
        try:
            return self._evaluate_condition(self.condition, context)
        except Exception:
            return None

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the hook and return a result dict.

        This method can be overridden or replaced for testing.
        The default implementation delegates to type-specific handlers.

        Args:
            context: Context data passed to the hook.

        Returns:
            Result dict with 'blocked' key if the hook blocks execution.
        """
        # Default: no-op, returns empty result
        return {}

    def _evaluate_condition(
        self, condition: str, context: dict[str, Any]
    ) -> bool:
        """Simple condition evaluator.

        Supports patterns like:
        - "tool.name == 'Bash'"
        - "event == 'PreToolUse'"

        Returns None if the condition cannot be evaluated.
        """
        # Simple key presence check
        parts = condition.split("==")
        if len(parts) == 2:
            left = parts[0].strip()
            right = parts[1].strip().strip("'\"")

            # Navigate nested context: "tool.name" -> context["tool"]["name"]
            current: Any = context
            for part in left.split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return True  # Can't navigate, allow

            return str(current) == right

        # Default: allow if we can't parse
        return True
