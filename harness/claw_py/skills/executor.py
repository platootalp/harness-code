"""Skill executor with allowed-tools boundary checking.

Corresponds to TypeScript's skill execution logic in src/skills/ and
security boundary checking in src/security/.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .definition import SkillDefinition, ToolUseContext, matches_tool_pattern

if TYPE_CHECKING:
    from ..models.message import ContentBlock


# =============================================================================
# Exceptions
# =============================================================================


class SkillError(Exception):
    """Base exception for skill-related errors."""

    pass


class SecurityError(SkillError):
    """Raised when a skill attempts to call a disallowed tool."""

    pass


class SkillTimeoutError(SkillError):
    """Raised when skill execution times out."""

    pass


class SkillExecutionError(SkillError):
    """Raised when skill execution fails."""

    pass


class SkillMemoryError(SkillError):
    """Raised when skill exceeds memory limit."""

    pass


class ToolBoundaryError(SkillError):
    """Raised when a tool call violates allowed-tools boundary."""

    pass


# =============================================================================
# Tool Call Representation
# =============================================================================


@dataclass
class ToolCall:
    """Represents a tool call made during skill execution."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    input_json: str = ""


@dataclass
class ToolCallResult:
    """Result of a tool call."""

    tool_call: ToolCall
    output: str = ""
    error: str | None = None
    success: bool = True


# =============================================================================
# Skill Executor
# =============================================================================


@dataclass
class ExecutionResult:
    """Result of skill execution."""

    skill_name: str
    content: list[ContentBlock] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolCallResult] = field(default_factory=list)
    error: str | None = None
    duration_ms: float = 0.0
    tokens_used: int = 0


class SkillExecutor:
    """Skill execution engine with allowed-tools boundary checking.

    Executes skills with proper security boundaries, timeout handling,
    and tool call monitoring.

    Corresponds to TypeScript's skill execution logic and the
    allowed-tools boundary checking in the security system.
    """

    def __init__(
        self,
        tool_registry: Any | None = None,
        timeout: float = 30.0,
        max_memory_mb: int = 256,
        on_tool_call: Callable[[ToolCall], None] | None = None,
        on_tool_result: Callable[[ToolCallResult], None] | None = None,
    ) -> None:
        """Initialize the skill executor.

        Args:
            tool_registry: Optional tool registry for validation.
            timeout: Maximum execution time in seconds.
            max_memory_mb: Maximum memory usage in MB.
            on_tool_call: Optional callback for tool calls.
            on_tool_result: Optional callback for tool results.
        """
        self._tool_registry = tool_registry
        self._timeout = timeout
        self._max_memory_mb = max_memory_mb
        self._on_tool_call = on_tool_call
        self._on_tool_result = on_tool_result
        self._tool_calls: list[ToolCall] = []
        self._tool_results: list[ToolCallResult] = []

    def reset_tracking(self) -> None:
        """Reset tool call tracking for a new execution."""
        self._tool_calls = []
        self._tool_results = []

    def record_tool_call(self, tool_call: ToolCall) -> None:
        """Record a tool call for tracking.

        Args:
            tool_call: The tool call to record.
        """
        self._tool_calls.append(tool_call)
        if self._on_tool_call:
            self._on_tool_call(tool_call)

    def record_tool_result(self, result: ToolCallResult) -> None:
        """Record a tool result for tracking.

        Args:
            result: The tool call result to record.
        """
        self._tool_results.append(result)
        if self._on_tool_result:
            self._on_tool_result(result)

    def get_tool_calls(self) -> list[ToolCall]:
        """Get all recorded tool calls.

        Returns:
            List of recorded tool calls.
        """
        return list(self._tool_calls)

    def get_tool_results(self) -> list[ToolCallResult]:
        """Get all recorded tool results.

        Returns:
            List of recorded tool results.
        """
        return list(self._tool_results)

    # -------------------------------------------------------------------------
    # Tool Boundary Checking
    # -------------------------------------------------------------------------

    def check_tool_boundaries(
        self,
        skill: SkillDefinition,
        tool_calls: list[ToolCall] | None = None,
    ) -> list[ToolBoundaryViolation]:
        """Verify all tool calls are within allowed-tools boundary.

        Args:
            skill: The skill definition with allowed_tools.
            tool_calls: List of tool calls to check. If None, uses recorded calls.

        Returns:
            List of boundary violations (empty if all calls are valid).
        """
        if tool_calls is None:
            tool_calls = self._tool_calls

        violations: list[ToolBoundaryViolation] = []
        patterns = skill.get_allowed_tools_patterns()

        for tc in tool_calls:
            if not self._is_tool_allowed(tc.name, tc.arguments, patterns):
                violations.append(
                    ToolBoundaryViolation(
                        tool_call=tc,
                        skill=skill.name,
                        allowed_tools=skill.allowed_tools,
                        reason=f"Tool '{tc.name}' is not in allowed-tools: "
                        f"{sorted(skill.allowed_tools)}",
                    )
                )

        return violations

    def _is_tool_allowed(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        patterns: list[tuple[str, str | None]],
    ) -> bool:
        """Check if a tool call matches any allowed pattern.

        Args:
            tool_name: Name of the tool.
            tool_args: Arguments passed to the tool.
            patterns: List of (name, arg_pattern) tuples.

        Returns:
            True if the tool is allowed.
        """
        # If no allowed tools specified, allow all
        if not patterns:
            return True

        tool_arg = self._extract_argument_string(tool_args)

        for pattern_name, pattern_arg in patterns:
            if matches_tool_pattern(tool_name, tool_arg, pattern_name, pattern_arg):
                return True

        return False

    def _extract_tool_argument(self, tool_call: ToolCall) -> str | None:
        """Extract argument string from a tool call.

        Args:
            tool_call: The tool call.

        Returns:
            Argument string or None.
        """
        return self._extract_argument_string(tool_call.arguments)

    def _extract_argument_string(self, args: dict[str, Any]) -> str | None:
        """Extract a string argument from tool arguments.

        Tries common patterns: command, script, cmd, command_str, etc.

        Args:
            args: Tool arguments dict.

        Returns:
            Argument string or None.
        """
        # Try common argument keys
        for key in ("command", "cmd", "script", "command_str", "exec", "args"):
            if key in args:
                val = args[key]
                if isinstance(val, str):
                    return val

        # Try first string value
        for val in args.values():
            if isinstance(val, str):
                return val

        return None

    def validate_execution(
        self,
        skill: SkillDefinition,
        tool_calls: list[ToolCall] | None = None,
    ) -> None:
        """Validate tool calls against allowed-tools, raising if invalid.

        Args:
            skill: The skill definition.
            tool_calls: List of tool calls to validate.

        Raises:
            ToolBoundaryError: If any tool call violates boundaries.
        """
        violations = self.check_tool_boundaries(skill, tool_calls)
        if violations:
            first = violations[0]
            raise ToolBoundaryError(
                f"Skill '{first.skill}' attempted to call tool "
                f"'{first.tool_call.name}' which is not in allowed-tools: "
                f"{sorted(first.allowed_tools)}"
            )

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolUseContext,
    ) -> ExecutionResult:
        """Execute a skill with the given arguments.

        Args:
            skill: The skill definition to execute.
            args: Arguments for the skill.
            context: Execution context.

        Returns:
            ExecutionResult with content and tool calls.
        """
        import time

        self.reset_tracking()
        start = time.monotonic()

        try:
            # Generate prompt content
            if skill.get_prompt_for_command is not None:
                skill_args = args.get("skill_args", "")
                raw_content = skill.get_prompt_for_command(skill_args, context)
                # Handle both sync and async callbacks
                import inspect

                if inspect.iscoroutine(raw_content):
                    content = await raw_content
                else:
                    content = raw_content
            else:
                # Default: return skill instructions as content
                skill.load_full()
                content = [{"type": "text", "text": skill.instructions}]  # type: ignore[list-item]

            duration_ms = (time.monotonic() - start) * 1000

            return ExecutionResult(
                skill_name=skill.name,
                content=content,
                tool_calls=list(self._tool_calls),
                tool_results=list(self._tool_results),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            return ExecutionResult(
                skill_name=skill.name,
                content=[],
                tool_calls=list(self._tool_calls),
                tool_results=list(self._tool_results),
                error=str(e),
                duration_ms=duration_ms,
            )

    async def execute_with_timeout(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolUseContext,
    ) -> ExecutionResult:
        """Execute a skill with timeout protection.

        Args:
            skill: The skill definition to execute.
            args: Arguments for the skill.
            context: Execution context.

        Returns:
            ExecutionResult with content and tool calls.

        Raises:
            SkillTimeoutError: If execution exceeds timeout.
        """
        try:
            return await asyncio.wait_for(
                self.execute(skill, args, context),
                timeout=self._timeout,
            )
        except TimeoutError as err:
            raise SkillTimeoutError(
                f"Skill '{skill.name}' execution timed out after {self._timeout}s"
            ) from err

    def execute_sync(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolUseContext,
    ) -> ExecutionResult:
        """Synchronous skill execution (runs async executor).

        Args:
            skill: The skill definition to execute.
            args: Arguments for the skill.
            context: Execution context.

        Returns:
            ExecutionResult with content and tool calls.
        """
        import asyncio

        return asyncio.run(self.execute(skill, args, context))


# =============================================================================
# Tool Boundary Violation
# =============================================================================


@dataclass
class ToolBoundaryViolation:
    """Represents a tool call that violated allowed-tools boundary."""

    tool_call: ToolCall
    skill: str
    allowed_tools: list[str]
    reason: str


# =============================================================================
# Restricted Context Factory
# =============================================================================


def create_tool_restricted_context(
    original_context: ToolUseContext,
    allowed_tools: list[str],
) -> ToolUseContext:
    """Create a restricted tool context with allowed-tools applied.

    Args:
        original_context: The original execution context.
        allowed_tools: List of allowed tool patterns.

    Returns:
        New context with tool restrictions applied.
    """
    return ToolUseContext(
        session_id=original_context.session_id,
        cwd=original_context.cwd,
        get_app_state=original_context.get_app_state,
    )


# =============================================================================
# Global Executor
# =============================================================================

_global_executor: SkillExecutor | None = None


def get_global_executor() -> SkillExecutor:
    """Get the global skill executor instance.

    Returns:
        The global SkillExecutor singleton.
    """
    global _global_executor
    if _global_executor is None:
        _global_executor = SkillExecutor()
    return _global_executor
