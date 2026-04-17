"""
Tests for skills/forked.py - Forked execution support.
"""

from __future__ import annotations

import asyncio

import pytest

from src.claude_code.skills.definition import SkillDefinition, ToolUseContext
from src.claude_code.skills.forked import (
    ForkedExecutionContext,
    ForkedExecutionResult,
    ForkedSkillExecutor,
    execute_skill_forked,
    get_forked_executor,
    register_builtin_fork_handlers,
)


@pytest.fixture
def forked_executor() -> ForkedSkillExecutor:
    """Create a fresh ForkedSkillExecutor."""
    return ForkedSkillExecutor()


@pytest.fixture
def sample_skill() -> SkillDefinition:
    """Create a sample skill."""
    return SkillDefinition(name="test", context="inline")


@pytest.fixture
def forked_skill() -> SkillDefinition:
    """Create a forked-context skill."""
    return SkillDefinition(name="batch", context="fork", agent="general-purpose")


class TestForkedExecutionContext:
    """Tests for ForkedExecutionContext."""

    def test_defaults(self) -> None:
        """ForkedExecutionContext has correct defaults."""
        ctx = ForkedExecutionContext(skill_name="test")
        assert ctx.skill_name == "test"
        assert ctx.parent_session_id is None
        assert ctx.forked_session_id is None
        assert ctx.model is None
        assert ctx.agent_type == "general-purpose"
        assert ctx.allowed_tools == []
        assert ctx.timeout_seconds == 300.0

    def test_full_initialization(self) -> None:
        """ForkedExecutionContext can be fully initialized."""
        ctx = ForkedExecutionContext(
            skill_name="batch",
            parent_session_id="parent-1",
            forked_session_id="fork-1",
            model="claude-opus",
            agent_type="task",
            effort="high",
            timeout_seconds=600.0,
            max_tokens=10000,
        )
        assert ctx.parent_session_id == "parent-1"
        assert ctx.model == "claude-opus"
        assert ctx.effort == "high"
        assert ctx.max_tokens == 10000

    def test_is_forked_property(self) -> None:
        """is_forked always returns True."""
        ctx = ForkedExecutionContext(skill_name="test")
        assert ctx.is_forked is True


class TestForkedExecutionResult:
    """Tests for ForkedExecutionResult."""

    def test_defaults(self) -> None:
        """ForkedExecutionResult has correct defaults."""
        result = ForkedExecutionResult(skill_name="test")
        assert result.skill_name == "test"
        assert result.success is True
        assert result.content == []
        assert result.error is None
        assert result.tool_calls == 0
        assert result.tokens_used == 0
        assert result.duration_seconds == 0.0
        assert result.session_id is None


class TestForkedSkillExecutorInit:
    """Tests for ForkedSkillExecutor initialization."""

    def test_defaults(self) -> None:
        """ForkedSkillExecutor has correct defaults."""
        exec = ForkedSkillExecutor()
        assert exec._max_concurrent == 3
        assert exec._default_timeout == 300.0
        assert exec._handlers == {}
        assert exec._active_forks == {}

    def test_custom_values(self) -> None:
        """ForkedSkillExecutor accepts custom values."""
        exec = ForkedSkillExecutor(max_concurrent=5, default_timeout=120.0)
        assert exec._max_concurrent == 5
        assert exec._default_timeout == 120.0


class TestForkedSkillExecutorHandlers:
    """Tests for ForkedSkillExecutor handler management."""

    def test_register_handler(self, forked_executor: ForkedSkillExecutor) -> None:
        """register_handler adds a handler."""
        async def handler(**kwargs: object) -> object:
            return []

        forked_executor.register_handler("task", handler)
        assert "task" in forked_executor.list_handlers()
        assert forked_executor.get_handler("task") is handler

    def test_unregister_handler(self, forked_executor: ForkedSkillExecutor) -> None:
        """unregister_handler removes a handler."""
        async def handler(**kwargs: object) -> object:
            return []

        forked_executor.register_handler("task", handler)
        forked_executor.unregister_handler("task")
        assert forked_executor.get_handler("task") is None

    def test_list_handlers(self, forked_executor: ForkedSkillExecutor) -> None:
        """list_handlers returns all registered agent types."""
        async def gp(**kwargs: object) -> object:
            return []

        async def task(**kwargs: object) -> object:
            return []

        forked_executor.register_handler("general-purpose", gp)
        forked_executor.register_handler("task", task)
        handlers = forked_executor.list_handlers()
        assert "general-purpose" in handlers
        assert "task" in handlers


class TestForkedSkillExecutorExecute:
    """Tests for ForkedSkillExecutor.execute."""

    @pytest.mark.asyncio
    async def test_execute_inline_fallback(
        self, forked_executor: ForkedSkillExecutor, forked_skill: SkillDefinition
    ) -> None:
        """execute falls back to inline when no handler registered."""
        context = ToolUseContext()
        result = await forked_executor.execute(forked_skill, {}, context)
        # Falls back to inline since no handler registered
        assert result.skill_name == "batch"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_handler(
        self, forked_executor: ForkedSkillExecutor, forked_skill: SkillDefinition
    ) -> None:
        """execute uses registered handler."""
        async def handler(
            skill: SkillDefinition,
            args: dict,
            context: ForkedExecutionContext,
        ) -> list:
            return [{"type": "text", "text": "handled result"}]

        forked_executor.register_handler("general-purpose", handler)
        context = ToolUseContext()
        result = await forked_executor.execute(forked_skill, {}, context)
        assert result.success is True
        assert len(result.content) == 1

    @pytest.mark.asyncio
    async def test_execute_error_handling(
        self, forked_executor: ForkedSkillExecutor, forked_skill: SkillDefinition
    ) -> None:
        """execute returns error result on exception."""
        async def bad_handler(
            skill: SkillDefinition,
            args: dict,
            context: ForkedExecutionContext,
        ) -> list:
            raise ValueError("test error")

        forked_executor.register_handler("general-purpose", bad_handler)
        result = await forked_executor.execute(forked_skill, {}, ToolUseContext())
        assert result.success is False
        assert "test error" in (result.error or "")


class TestForkedSkillExecutorConcurrency:
    """Tests for ForkedSkillExecutor concurrency control."""

    @pytest.mark.asyncio
    async def test_concurrency_limit(self) -> None:
        """respects max_concurrent limit."""
        exec = ForkedSkillExecutor(max_concurrent=2, default_timeout=5.0)
        skill = SkillDefinition(name="test", context="fork")

        async def slow_handler(
            skill: SkillDefinition,
            args: dict,
            context: ForkedExecutionContext,
        ) -> list:
            return [{"type": "text", "text": "done"}]

        exec.register_handler("general-purpose", slow_handler)

        # Should not raise even with many concurrent calls
        tasks = [
            exec.execute(skill, {}, ToolUseContext())
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5


class TestRegisterBuiltinForkHandlers:
    """Tests for register_builtin_fork_handlers."""

    def test_registers_handlers(self) -> None:
        """register_builtin_fork_handlers registers built-in handlers."""
        exec = ForkedSkillExecutor()
        register_builtin_fork_handlers(exec)
        assert "general-purpose" in exec.list_handlers()
        assert "task" in exec.list_handlers()


class TestExecuteSkillForked:
    """Tests for execute_skill_forked helper."""

    @pytest.mark.asyncio
    async def test_inline_skill_runs_inline(self) -> None:
        """inline skill executes without forking."""
        skill = SkillDefinition(
            name="test",
            context="inline",
            instructions="Test instructions",
        )
        skill._loaded = True
        result = await execute_skill_forked(skill, {}, ToolUseContext())
        assert result.success is True
        assert len(result.content) == 1

    @pytest.mark.asyncio
    async def test_fork_skill_uses_executor(self) -> None:
        """fork skill uses ForkedSkillExecutor."""
        skill = SkillDefinition(name="test", context="fork", agent="general-purpose")
        result = await execute_skill_forked(skill, {}, ToolUseContext())
        # Falls back to inline since no handler registered
        assert result.skill_name == "test"


class TestGlobalForkedExecutor:
    """Tests for global forked executor."""

    def test_get_forked_executor_singleton(self) -> None:
        """get_forked_executor returns the same instance."""
        exec1 = get_forked_executor()
        exec2 = get_forked_executor()
        assert exec1 is exec2

    def test_global_executor_has_builtin_handlers(self) -> None:
        """global executor has built-in handlers registered."""
        exec = get_forked_executor()
        assert "general-purpose" in exec.list_handlers()
        assert "task" in exec.list_handlers()
