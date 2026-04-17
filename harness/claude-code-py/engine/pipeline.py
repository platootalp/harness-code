"""Query pipeline state and parameters.

TypeScript equivalent: src/query.ts State type, src/query/deps.ts, src/query/config.ts
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from claude_code.models.message import Message


# =============================================================================
# Query Source
# =============================================================================


class QuerySource(StrEnum):
    """Source/origin of a query request."""

    REPL_MAIN_THREAD = "repl_main_thread"
    REPL_BACKGROUND = "repl_background"
    SDK = "sdk"
    AGENT = "agent"
    TASK = "task"
    COMMAND = "command"
    AUTO = "auto"


# =============================================================================
# Query Dependencies
# =============================================================================


class CallModelFn(Protocol):
    """Protocol for the model calling function with streaming."""

    async def __call__(
        self,
        messages: list[dict[str, Any]],
        system: str | None,
        tools: list[dict[str, Any]] | None,
        tool_use_context: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        ...


@dataclass
class QueryDeps:
    """I/O dependencies for the query pipeline."""

    call_model: CallModelFn
    uuid_fn: Callable[[], str] = field(default_factory=lambda: str(uuid.uuid4()))  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not callable(self.call_model):
            raise TypeError("call_model must be callable")


def production_deps() -> QueryDeps:
    """Create production dependencies with real implementations."""
    return QueryDeps(call_model=_default_call_model)


async def _default_call_model(
    messages: list[dict[str, Any]],
    system: str | None,
    tools: list[dict[str, Any]] | None,
    tool_use_context: dict[str, Any],
    **kwargs: Any,
) -> Any:
    """Default model call - should be replaced with actual API call."""
    raise NotImplementedError(
        "Default call_model not implemented. "
        "Use production_deps() with actual API client."
    )


# =============================================================================
# Query Configuration
# =============================================================================


@dataclass(frozen=True)
class QueryConfig:
    """Immutable configuration snapshotted once at query() entry."""

    session_id: str
    streaming_tool_execution: bool = False
    emit_tool_use_summaries: bool = False
    is_ant: bool = False
    fast_mode_enabled: bool = True


def build_query_config() -> QueryConfig:
    """Build query config from current environment."""
    import os

    return QueryConfig(
        session_id=str(uuid.uuid4()),
        streaming_tool_execution=False,
        emit_tool_use_summaries=bool(
            os.environ.get("CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES")
        ),
        is_ant=os.environ.get("USER_TYPE") == "ant",
        fast_mode_enabled=not bool(
            os.environ.get("CLAUDE_CODE_DISABLE_FAST_MODE")
        ),
    )


# =============================================================================
# Query Parameters
# =============================================================================


@dataclass
class QueryParams:
    """Parameters for query execution.

    Attributes:
        messages: Conversation history to send with the query.
        system_prompt: Optional system prompt override.
        tools: List of tool definitions available for this query.
        max_output_tokens: Maximum tokens to generate in response.
        metadata: Additional metadata for the query.
        user_context: Additional user-provided context values.
        system_context: Additional system-provided context values.
        can_use_tool: Callback to check if a tool can be used.
        tool_use_context: Context for tool execution.
        fallback_model: Optional fallback model name.
        query_source: Source/origin of the query.
        max_output_tokens_override: Override for max output tokens.
        max_turns: Maximum number of turns before stopping.
        skip_cache_write: Skip writing to message cache.
        task_budget: Output token budget for the entire turn.
        deps: I/O dependencies (defaults to production).
    """

    messages: list[Message]
    system_prompt: str | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    user_context: dict[str, str] = field(default_factory=dict)
    system_context: dict[str, str] = field(default_factory=dict)
    can_use_tool: Callable[[str, Any], bool] | None = None
    tool_use_context: dict[str, Any] | None = None
    fallback_model: str | None = None
    query_source: QuerySource = QuerySource.REPL_MAIN_THREAD
    max_output_tokens_override: int | None = None
    max_turns: int | None = None
    skip_cache_write: bool = False
    task_budget: dict[str, int] | None = None
    deps: QueryDeps | None = None

    def __post_init__(self) -> None:
        if self.deps is None:
            self.deps = production_deps()

    def get_deps(self) -> QueryDeps:
        if self.deps is None:
            return production_deps()
        return self.deps


# =============================================================================
# Query State
# =============================================================================


@dataclass
class QueryState:
    """State carried across query loop iterations.

    TypeScript equivalent: src/query.ts::State

    Tracks the current state during multi-turn query execution including
    message history, context management, and error recovery tracking.

    Attributes:
        messages: Current conversation history.
        turn_count: Number of turns completed in this query.
        auto_compact_tracking: Tracking data for auto-compaction.
        has_attempted_reactive_compact: Whether reactive compaction was attempted.
        max_output_tokens_recovery_count: Number of output token recovery attempts.
        max_output_tokens_override: Override for max output tokens.
        pending_tool_use_summary: Summary of pending tool uses.
        stop_hook_active: Whether a stop hook is currently active.
        transition: Continuation type for the next iteration.
    """

    messages: list[Message]
    turn_count: int = 0
    auto_compact_tracking: dict[str, Any] | None = None
    has_attempted_reactive_compact: bool = False
    max_output_tokens_recovery_count: int = 0
    max_output_tokens_override: int | None = None
    pending_tool_use_summary: Any = None
    stop_hook_active: bool = False
    transition: str | None = None

    def copy_with(self, **kwargs: Any) -> QueryState:
        """Create a copy with updated fields.

        Args:
            **kwargs: Fields to update in the copy.

        Returns:
            A new QueryState with the updated fields.
        """
        new_state = copy.copy(self)
        for key, value in kwargs.items():
            setattr(new_state, key, value)
        return new_state


def create_initial_state(params: QueryParams) -> QueryState:
    """Create initial query state from query parameters.

    Args:
        params: The query parameters.

    Returns:
        Initial QueryState for the first iteration.
    """
    return QueryState(
        messages=list(params.messages),
        max_output_tokens_override=params.max_output_tokens_override,
        auto_compact_tracking=None,
        stop_hook_active=False,
        max_output_tokens_recovery_count=0,
        has_attempted_reactive_compact=False,
        turn_count=1,
        pending_tool_use_summary=None,
        transition=None,
    )


# =============================================================================
# Query Result
# =============================================================================


class QueryResultStatus(StrEnum):
    """Status of a query result."""

    SUCCESS = "success"
    STOPPED = "stopped"
    ERROR = "error"
    MAX_TURNS_REACHED = "max_turns_reached"
    MAX_OUTPUT_TOKENS = "max_output_tokens"
    RATE_LIMITED = "rate_limited"
    ABORTED = "aborted"


@dataclass
class QueryResult:
    """Result from query execution.

    Attributes:
        reason: Why the query ended (completed, max_turns, budget_exceeded, abort).
        messages: Final conversation history after query execution.
        total_tokens: Total tokens consumed during the query.
        total_cost: Total estimated cost in USD.
        status: The outcome status of the query.
        total_usage: Token usage statistics.
        stop_reason: Why the query stopped (if applicable).
        error: Error message (if status is ERROR).
    """

    reason: str
    messages: list[Message] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    status: QueryResultStatus = QueryResultStatus.SUCCESS
    total_usage: dict[str, int] | None = None
    stop_reason: str | None = None
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status == QueryResultStatus.SUCCESS

    @property
    def is_error(self) -> bool:
        return self.status == QueryResultStatus.ERROR

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "messages": self.messages,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "status": self.status.value,
            "total_usage": self.total_usage,
            "stop_reason": self.stop_reason,
            "error": self.error,
        }


# =============================================================================
# Token Budget
# =============================================================================


@dataclass
class BudgetTracker:
    """Tracks token budget consumption across query iterations."""

    continuation_count: int = 0
    last_delta_tokens: int = 0
    last_global_turn_tokens: int = 0
    started_at: float = field(default_factory=lambda: __import__("time").time())


def create_budget_tracker() -> BudgetTracker:
    """Create a new budget tracker."""
    return BudgetTracker()


class BudgetDecision(StrEnum):
    """Decision from budget check."""

    CONTINUE = "continue"
    STOP = "stop"


@dataclass
class BudgetDecisionResult:
    """Result of a budget check decision."""

    action: BudgetDecision
    nudge_message: str | None = None
    continuation_count: int = 0
    pct: int = 0
    turn_tokens: int = 0
    budget: int = 0
    diminishing_returns: bool = False
    duration_ms: int = 0


def check_token_budget(
    tracker: BudgetTracker,
    agent_id: str | None,
    budget: int | None,
    global_turn_tokens: int,
) -> BudgetDecisionResult:
    """Check if token budget allows continuing the query.

    Args:
        tracker: Budget tracker with current state.
        agent_id: Agent ID (if sub-agent, budget doesn't apply).
        budget: Token budget limit.
        global_turn_tokens: Current global turn token count.

    Returns:
        BudgetDecisionResult indicating whether to continue or stop.
    """
    import time as time_module

    if agent_id or budget is None or budget <= 0:
        return BudgetDecisionResult(action=BudgetDecision.STOP)

    turn_tokens = global_turn_tokens
    pct = round((turn_tokens / budget) * 100) if budget > 0 else 0
    delta_since_last = global_turn_tokens - tracker.last_global_turn_tokens

    # Diminishing returns: 3+ continuations with small deltas
    is_diminishing = (
        tracker.continuation_count >= 3
        and delta_since_last < 500
        and tracker.last_delta_tokens < 500
    )

    if not is_diminishing and turn_tokens < budget * 0.9:
        tracker.continuation_count += 1
        tracker.last_delta_tokens = delta_since_last
        tracker.last_global_turn_tokens = global_turn_tokens

        return BudgetDecisionResult(
            action=BudgetDecision.CONTINUE,
            nudge_message=f"Continuing: {pct}% of budget used ({turn_tokens}/{budget} tokens)",
            continuation_count=tracker.continuation_count,
            pct=pct,
            turn_tokens=turn_tokens,
            budget=budget,
        )

    if is_diminishing or tracker.continuation_count > 0:
        return BudgetDecisionResult(
            action=BudgetDecision.STOP,
            continuation_count=tracker.continuation_count,
            pct=pct,
            turn_tokens=turn_tokens,
            budget=budget,
            diminishing_returns=is_diminishing,
            duration_ms=int((time_module.time() - tracker.started_at) * 1000),
        )

    return BudgetDecisionResult(action=BudgetDecision.STOP)
