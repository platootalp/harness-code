"""
Tests for engine/pipeline.py - Query pipeline data structures.
"""

from __future__ import annotations

import pytest
from claude_code.engine.pipeline import (
    BudgetDecision,
    BudgetDecisionResult,
    BudgetTracker,
    QueryParams,
    QueryResult,
    QueryResultStatus,
    QuerySource,
    QueryState,
    check_token_budget,
    create_budget_tracker,
    create_initial_state,
)


class TestQuerySource:
    """Tests for QuerySource enum."""

    def test_values(self) -> None:
        """Test that enum has expected values."""
        assert QuerySource.REPL_MAIN_THREAD.value == "repl_main_thread"
        assert QuerySource.REPL_BACKGROUND.value == "repl_background"
        assert QuerySource.SDK.value == "sdk"
        assert QuerySource.AGENT.value == "agent"
        assert QuerySource.TASK.value == "task"
        assert QuerySource.COMMAND.value == "command"
        assert QuerySource.AUTO.value == "auto"

    def test_from_string(self) -> None:
        """Test creating from string value."""
        assert QuerySource("repl_main_thread") == QuerySource.REPL_MAIN_THREAD
        assert QuerySource("sdk") == QuerySource.SDK


class TestQueryParams:
    """Tests for QueryParams dataclass."""

    def test_create_minimal(self) -> None:
        """Test creating with minimal parameters."""
        params = QueryParams(messages=[])
        assert params.messages == []
        assert params.system_prompt is None
        assert params.deps is not None

    def test_create_with_tools(self) -> None:
        """Test creating with tools."""
        tools = [{"name": "bash", "description": "Run bash"}]
        params = QueryParams(messages=[], tools=tools)
        assert len(params.tools) == 1
        assert params.tools[0]["name"] == "bash"

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        params = QueryParams(messages=[])
        assert params.user_context == {}
        assert params.system_context == {}
        assert params.can_use_tool is None
        assert params.tool_use_context is None
        assert params.fallback_model is None
        assert params.query_source == QuerySource.REPL_MAIN_THREAD
        assert params.max_output_tokens_override is None
        assert params.max_turns is None
        assert params.skip_cache_write is False
        assert params.task_budget is None

    def test_get_deps(self) -> None:
        """Test getting dependencies."""
        params = QueryParams(messages=[])
        deps = params.get_deps()
        assert deps is not None
        assert callable(deps.call_model)


class TestQueryState:
    """Tests for QueryState dataclass."""

    def test_create(self) -> None:
        """Test creating QueryState."""
        messages = [{"role": "user", "content": "Hello"}]
        state = QueryState(messages=messages, turn_count=0)
        assert state.messages == messages
        assert state.turn_count == 0

    def test_default_values(self) -> None:
        """Test default values."""
        state = QueryState(messages=[])
        assert state.turn_count == 0
        assert state.auto_compact_tracking is None
        assert state.has_attempted_reactive_compact is False
        assert state.max_output_tokens_recovery_count == 0
        assert state.max_output_tokens_override is None
        assert state.pending_tool_use_summary is None
        assert state.stop_hook_active is False
        assert state.transition is None

    def test_copy_with(self) -> None:
        """Test creating a copy with updated fields."""
        state = QueryState(messages=[], turn_count=1)
        updated = state.copy_with(turn_count=2)

        assert updated.turn_count == 2
        assert updated.messages == state.messages
        # Original should be unchanged
        assert state.turn_count == 1


class TestCreateInitialState:
    """Tests for create_initial_state function."""

    def test_from_params(self) -> None:
        """Test creating initial state from params."""
        from claude_code.models.message import ContentBlock, Message

        messages = [Message(id="1", role="user", content_blocks=[ContentBlock(text="Hello")])]
        params = QueryParams(
            messages=messages,
            max_output_tokens_override=4096,
        )
        state = create_initial_state(params)

        assert len(state.messages) == 1
        assert state.turn_count == 1
        assert state.max_output_tokens_override == 4096

    def test_empty_messages(self) -> None:
        """Test with empty messages."""
        from claude_code.models.message import Message

        params = QueryParams(messages=[])
        state = create_initial_state(params)
        assert state.messages == []


class TestQueryResultStatus:
    """Tests for QueryResultStatus enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert QueryResultStatus.SUCCESS.value == "success"
        assert QueryResultStatus.STOPPED.value == "stopped"
        assert QueryResultStatus.ERROR.value == "error"
        assert QueryResultStatus.MAX_TURNS_REACHED.value == "max_turns_reached"
        assert QueryResultStatus.MAX_OUTPUT_TOKENS.value == "max_output_tokens"
        assert QueryResultStatus.RATE_LIMITED.value == "rate_limited"
        assert QueryResultStatus.ABORTED.value == "aborted"


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_create_success(self) -> None:
        """Test creating a success result."""
        messages = [{"role": "assistant", "content": "Hello!"}]
        result = QueryResult(
            reason="completed",
            messages=messages,
            status=QueryResultStatus.SUCCESS,
        )
        assert result.status == QueryResultStatus.SUCCESS
        assert len(result.messages) == 1

    def test_is_success(self) -> None:
        """Test is_success property."""
        result = QueryResult(reason="completed", status=QueryResultStatus.SUCCESS)
        assert result.is_success is True

        error_result = QueryResult(reason="error", status=QueryResultStatus.ERROR)
        assert error_result.is_success is False

    def test_is_error(self) -> None:
        """Test is_error property."""
        result = QueryResult(
            reason="error",
            status=QueryResultStatus.ERROR,
            error="Something went wrong",
        )
        assert result.is_error is True

        success_result = QueryResult(reason="completed", status=QueryResultStatus.SUCCESS)
        assert success_result.is_error is False

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        result = QueryResult(
            reason="completed",
            messages=[{"role": "user", "content": "Hi"}],
            total_usage={"input_tokens": 100, "output_tokens": 50},
            status=QueryResultStatus.SUCCESS,
            stop_reason="complete",
        )
        d = result.to_dict()

        assert d["status"] == "success"
        assert len(d["messages"]) == 1
        assert d["total_usage"]["input_tokens"] == 100


class TestBudgetTracker:
    """Tests for BudgetTracker dataclass."""

    def test_create(self) -> None:
        """Test creating a budget tracker."""
        tracker = BudgetTracker()
        assert tracker.continuation_count == 0
        assert tracker.last_delta_tokens == 0
        assert tracker.last_global_turn_tokens == 0
        assert tracker.started_at > 0


class TestCreateBudgetTracker:
    """Tests for create_budget_tracker function."""

    def test_returns_budget_tracker(self) -> None:
        """Test that it returns a BudgetTracker."""
        tracker = create_budget_tracker()
        assert isinstance(tracker, BudgetTracker)
        assert tracker.continuation_count == 0


class TestCheckTokenBudget:
    """Tests for check_token_budget function."""

    def test_stop_for_agent(self) -> None:
        """Test that sub-agents always stop."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id="sub-agent-123",
            budget=100000,
            global_turn_tokens=50000,
        )
        assert result.action == BudgetDecision.STOP

    def test_stop_for_null_budget(self) -> None:
        """Test that null budget stops."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=None,
            global_turn_tokens=50000,
        )
        assert result.action == BudgetDecision.STOP

    def test_stop_for_zero_budget(self) -> None:
        """Test that zero budget stops."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=0,
            global_turn_tokens=50000,
        )
        assert result.action == BudgetDecision.STOP

    def test_continue_under_threshold(self) -> None:
        """Test continuing when under 90% threshold."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=100000,
            global_turn_tokens=50000,  # 50% of budget
        )
        assert result.action == BudgetDecision.CONTINUE
        assert result.pct == 50
        assert tracker.continuation_count == 1

    def test_stop_at_threshold(self) -> None:
        """Test stopping at or above 90% threshold."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=100000,
            global_turn_tokens=95000,  # 95% of budget
        )
        assert result.action == BudgetDecision.STOP

    def test_diminishing_returns(self) -> None:
        """Test diminishing returns detection."""
        tracker = BudgetTracker(
            continuation_count=3,
            last_delta_tokens=100,
            last_global_turn_tokens=95000,
        )
        # This should trigger diminishing returns because:
        # - continuation_count >= 3 (True, it's 3)
        # - delta_since_last < 500 (True, 96000 - 95000 = 1000, which is NOT < 500)
        # Wait, 96000 - 95000 = 1000, which is NOT < 500
        # Let me fix this to use a smaller delta
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=100000,
            global_turn_tokens=95100,  # Only 100 new tokens since last check
        )
        assert result.action == BudgetDecision.STOP
        assert result.diminishing_returns is True

    def test_pct_calculation(self) -> None:
        """Test percentage calculation."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=200000,
            global_turn_tokens=50000,
        )
        assert result.pct == 25
        assert result.turn_tokens == 50000
        assert result.budget == 200000

    def test_continuation_count_increments(self) -> None:
        """Test that continuation count increments on continue."""
        tracker = BudgetTracker()

        # First continue
        result1 = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=100000,
            global_turn_tokens=30000,
        )
        assert result1.continuation_count == 1

        # Second continue
        result2 = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=100000,
            global_turn_tokens=60000,
        )
        assert result2.continuation_count == 2

    def test_nudge_message_contains_pct(self) -> None:
        """Test that nudge message contains percentage."""
        tracker = BudgetTracker()
        result = check_token_budget(
            tracker=tracker,
            agent_id=None,
            budget=100000,
            global_turn_tokens=50000,
        )
        assert "50%" in (result.nudge_message or "")
