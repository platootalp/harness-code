"""Forked execution support for skills (sub-agent execution).

Corresponds to TypeScript's forkedAgent.ts and related sub-agent
execution logic in src/skills/.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .definition import SkillDefinition, ToolUseContext

if TYPE_CHECKING:
    from ..models.message import ContentBlock


# =============================================================================
# Forked Execution Context
# =============================================================================


@dataclass
class ForkedExecutionContext:
    """Context for a forked (sub-agent) skill execution.

    Represents a separate execution context with its own settings,
    tool restrictions, and budget.
    """

    skill_name: str
    parent_session_id: str | None = None
    forked_session_id: str | None = None

    # Execution settings
    model: str | None = None
    agent_type: str = "general-purpose"
    effort: str | None = None
    timeout_seconds: float = 300.0

    # Tool restrictions (from allowed-tools)
    allowed_tools: list[str] = field(default_factory=list)

    # Context from parent
    cwd: str | None = None
    environment: dict[str, str] = field(default_factory=dict)

    # Budget constraints
    max_tokens: int | None = None
    max_tool_calls: int | None = None

    # Callbacks
    on_result: Callable[[list[ContentBlock]], None] | None = None
    on_error: Callable[[Exception], None] | None = None
    on_progress: Callable[[str], None] | None = None

    @property
    def is_forked(self) -> bool:
        """Whether this is a forked execution context."""
        return True


# =============================================================================
# Forked Execution Result
# =============================================================================


@dataclass
class ForkedExecutionResult:
    """Result of a forked skill execution."""

    skill_name: str
    success: bool = True
    content: list[ContentBlock] = field(default_factory=list)
    error: str | None = None
    tool_calls: int = 0
    tokens_used: int = 0
    duration_seconds: float = 0.0
    session_id: str | None = None


# =============================================================================
# Forked Executor
# =============================================================================


class ForkedSkillExecutor:
    """Executor for forked (sub-agent) skill execution.

    Runs skills in a separate execution context with dedicated budget
    and tool restrictions. Corresponds to TypeScript's forkedAgent.ts.

    Attributes:
        _handlers: Registered fork handlers by agent type.
        _active_forks: Currently running forked executions.
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        default_timeout: float = 300.0,
    ) -> None:
        """Initialize the forked executor.

        Args:
            max_concurrent: Maximum concurrent forked executions.
            default_timeout: Default timeout for forked executions.
        """
        self._max_concurrent = max_concurrent
        self._default_timeout = default_timeout
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._active_forks: dict[str, ForkedExecutionContext] = {}
        self._semaphore: asyncio.Semaphore | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create the concurrency semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    def register_handler(
        self,
        agent_type: str,
        handler: Callable[..., Any],
    ) -> None:
        """Register a handler for an agent type.

        Args:
            agent_type: The agent type (e.g., "general-purpose", "task").
            handler: Async function to handle the execution.
        """
        self._handlers[agent_type] = handler

    def unregister_handler(self, agent_type: str) -> None:
        """Unregister a handler for an agent type.

        Args:
            agent_type: The agent type to unregister.
        """
        if agent_type in self._handlers:
            del self._handlers[agent_type]

    def get_handler(self, agent_type: str) -> Callable[..., Any] | None:
        """Get the handler for an agent type.

        Args:
            agent_type: The agent type.

        Returns:
            The handler function or None.
        """
        return self._handlers.get(agent_type)

    def list_handlers(self) -> list[str]:
        """List registered agent types.

        Returns:
            List of agent type names.
        """
        return list(self._handlers.keys())

    async def execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolUseContext,
        forked_context: ForkedExecutionContext | None = None,
    ) -> ForkedExecutionResult:
        """Execute a skill in a forked (sub-agent) context.

        Args:
            skill: The skill definition to execute.
            args: Arguments for the skill.
            context: Parent execution context.
            forked_context: Optional forked execution context.

        Returns:
            ForkedExecutionResult with sub-agent output.
        """
        import time

        if forked_context is None:
            forked_context = self._create_forked_context(skill, context)

        start_time = time.monotonic()

        # Check concurrency limit
        semaphore = self._get_semaphore()

        async with semaphore:
            return await self._do_execute(
                skill, args, context, forked_context, start_time
            )

    async def _do_execute(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ToolUseContext,
        forked_context: ForkedExecutionContext,
        start_time: float,
    ) -> ForkedExecutionResult:
        """Internal execution implementation."""
        import time

        try:
            # Get handler for agent type
            handler = self.get_handler(forked_context.agent_type)
            if handler is None:
                # Use default inline execution
                return await self._execute_inline_fallback(
                    skill, args, forked_context, start_time
                )

            # Execute via handler
            result = await handler(
                skill=skill,
                args=args,
                context=forked_context,
            )

            duration = time.monotonic() - start_time

            return ForkedExecutionResult(
                skill_name=skill.name,
                success=True,
                content=result if isinstance(result, list) else [result],
                duration_seconds=duration,
                session_id=forked_context.forked_session_id,
            )

        except Exception as e:
            duration = time.monotonic() - start_time
            return ForkedExecutionResult(
                skill_name=skill.name,
                success=False,
                error=str(e),
                duration_seconds=duration,
                session_id=forked_context.forked_session_id,
            )

    async def _execute_inline_fallback(
        self,
        skill: SkillDefinition,
        args: dict[str, Any],
        forked_context: ForkedExecutionContext,
        start_time: float,
    ) -> ForkedExecutionResult:
        """Fallback to inline execution when no handler is registered.

        This allows forked skills to work even without a dedicated
        agent handler, by executing them inline with the parent context.
        """
        import time

        # Get prompt content
        if skill.get_prompt_for_command is not None:
            skill_context = ToolUseContext(
                session_id=forked_context.forked_session_id,
                cwd=forked_context.cwd,
            )
            content = skill.get_prompt_for_command(
                args.get("skill_args", ""), skill_context
            )
        else:
            skill.load_full()
            content = [{"type": "text", "text": skill.instructions}]  # type: ignore[list-item]

        duration = time.monotonic() - start_time

        return ForkedExecutionResult(
            skill_name=skill.name,
            success=True,
            content=content,
            duration_seconds=duration,
            session_id=forked_context.forked_session_id,
        )

    def _create_forked_context(
        self,
        skill: SkillDefinition,
        parent_context: ToolUseContext,
    ) -> ForkedExecutionContext:
        """Create a forked execution context from skill and parent.

        Args:
            skill: The skill being executed.
            parent_context: The parent execution context.

        Returns:
            New forked execution context.
        """
        import uuid

        forked_context = ForkedExecutionContext(
            skill_name=skill.name,
            parent_session_id=parent_context.session_id,
            forked_session_id=str(uuid.uuid4()),
            model=skill.model,
            agent_type=skill.agent or "general-purpose",
            effort=skill.effort,
            allowed_tools=list(skill.allowed_tools),
            cwd=parent_context.cwd or os.getcwd(),
            timeout_seconds=self._default_timeout,
        )

        return forked_context

    def get_active_count(self) -> int:
        """Get the number of active forked executions.

        Returns:
            Number of currently running forked executions.
        """
        return len(self._active_forks)

    def cancel_all(self) -> None:
        """Cancel all active forked executions."""
        for fork_id in list(self._active_forks.keys()):
            self._active_forks.pop(fork_id, None)


# =============================================================================
# Built-in Fork Handler Registration
# =============================================================================


def register_builtin_fork_handlers(executor: ForkedSkillExecutor) -> None:
    """Register built-in fork handlers for standard agent types.

    Args:
        executor: The forked executor to register handlers with.
    """

    async def general_purpose_handler(
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ForkedExecutionContext,
    ) -> list[ContentBlock]:
        """Handler for general-purpose agent type.

        In a full implementation, this would spawn a new agent session.
        """
        if skill.get_prompt_for_command is not None:
            return skill.get_prompt_for_command(
                args.get("skill_args", ""),
                ToolUseContext(
                    session_id=context.forked_session_id,
                    cwd=context.cwd,
                ),
            )

        skill.load_full()
        return [{"type": "text", "text": skill.instructions}]  # type: ignore[list-item]

    async def task_handler(
        skill: SkillDefinition,
        args: dict[str, Any],
        context: ForkedExecutionContext,
    ) -> list[ContentBlock]:
        """Handler for task agent type."""
        if skill.get_prompt_for_command is not None:
            return skill.get_prompt_for_command(
                args.get("skill_args", ""),
                ToolUseContext(
                    session_id=context.forked_session_id,
                    cwd=context.cwd,
                ),
            )

        skill.load_full()
        return [{"type": "text", "text": skill.instructions}]  # type: ignore[list-item]

    executor.register_handler("general-purpose", general_purpose_handler)
    executor.register_handler("task", task_handler)


# =============================================================================
# Global Executor
# =============================================================================

_global_forked_executor: ForkedSkillExecutor | None = None


def get_forked_executor() -> ForkedSkillExecutor:
    """Get the global forked skill executor.

    Returns:
        The global ForkedSkillExecutor singleton.
    """
    global _global_forked_executor
    if _global_forked_executor is None:
        _global_forked_executor = ForkedSkillExecutor()
        register_builtin_fork_handlers(_global_forked_executor)
    return _global_forked_executor


# =============================================================================
# Skill Execution with Fork Support
# =============================================================================


async def execute_skill_forked(
    skill: SkillDefinition,
    args: dict[str, Any],
    context: ToolUseContext,
    executor: ForkedSkillExecutor | None = None,
) -> ForkedExecutionResult:
    """Execute a skill, using forked context if specified.

    Args:
        skill: The skill to execute.
        args: Execution arguments.
        context: Parent execution context.
        executor: Optional forked executor (uses global if not provided).

    Returns:
        ForkedExecutionResult.
    """
    if executor is None:
        executor = get_forked_executor()

    if skill.context == "fork":
        return await executor.execute(skill, args, context)

    # Inline execution
    skill.load_full()
    if skill.get_prompt_for_command is not None:
        content = skill.get_prompt_for_command(
            args.get("skill_args", ""), context
        )
    else:
        content = [{"type": "text", "text": skill.instructions}]  # type: ignore[list-item]

    return ForkedExecutionResult(
        skill_name=skill.name,
        success=True,
        content=content,
    )
