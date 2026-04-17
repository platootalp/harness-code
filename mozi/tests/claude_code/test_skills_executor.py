"""
Tests for skills/executor.py - SkillExecutor and tool boundary checking.
"""

from __future__ import annotations

import asyncio

import pytest

from src.claude_code.skills.definition import SkillDefinition, ToolUseContext
from src.claude_code.skills.executor import (
    ExecutionResult,
    SkillExecutor,
    ToolBoundaryViolation,
    ToolCall,
    ToolCallResult,
    create_tool_restricted_context,
    get_global_executor,
)


@pytest.fixture
def executor() -> SkillExecutor:
    """Create a fresh SkillExecutor."""
    return SkillExecutor()


@pytest.fixture
def sample_skill() -> SkillDefinition:
    """Create a sample skill."""
    return SkillDefinition(
        name="simplify",
        description="Simplify code",
        allowed_tools=["Read", "Glob", "Bash(git:*)"],
    )


class TestSkillExecutorInit:
    """Tests for SkillExecutor initialization."""

    def test_defaults(self) -> None:
        """SkillExecutor has correct defaults."""
        exec = SkillExecutor()
        assert exec._timeout == 30.0
        assert exec._max_memory_mb == 256
        assert exec._tool_calls == []
        assert exec._tool_results == []

    def test_custom_values(self) -> None:
        """SkillExecutor accepts custom timeout and memory."""
        exec = SkillExecutor(timeout=60.0, max_memory_mb=512)
        assert exec._timeout == 60.0
        assert exec._max_memory_mb == 512

    def test_callbacks(self) -> None:
        """SkillExecutor accepts callbacks."""
        tc_calls: list[ToolCall] = []
        tr_calls: list[ToolCallResult] = []
        exec = SkillExecutor(
            on_tool_call=lambda tc: tc_calls.append(tc),
            on_tool_result=lambda tr: tr_calls.append(tr),
        )
        assert exec._on_tool_call is not None
        assert exec._on_tool_result is not None


class TestSkillExecutorTracking:
    """Tests for SkillExecutor tool call tracking."""

    def test_reset_tracking(self, executor: SkillExecutor) -> None:
        """reset_tracking clears recorded calls."""
        tc = ToolCall(name="Read", arguments={"path": "foo.py"})
        executor.record_tool_call(tc)
        assert len(executor.get_tool_calls()) == 1
        executor.reset_tracking()
        assert executor.get_tool_calls() == []

    def test_record_tool_call(self, executor: SkillExecutor) -> None:
        """record_tool_call adds to recorded calls."""
        tc = ToolCall(name="Read", arguments={"path": "foo.py"})
        executor.record_tool_call(tc)
        assert tc in executor.get_tool_calls()

    def test_record_tool_result(self, executor: SkillExecutor) -> None:
        """record_tool_result adds to recorded results."""
        tc = ToolCall(name="Read", arguments={"path": "foo.py"})
        tr = ToolCallResult(tool_call=tc, output="file content")
        executor.record_tool_result(tr)
        assert tr in executor.get_tool_results()


class TestSkillExecutorBoundaryChecking:
    """Tests for SkillExecutor tool boundary checking."""

    def test_check_tool_boundaries_all_allowed(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """check_tool_boundaries returns empty when all tools allowed."""
        calls = [
            ToolCall(name="Read"),
            ToolCall(name="Glob"),
        ]
        violations = executor.check_tool_boundaries(sample_skill, calls)
        assert violations == []

    def test_check_tool_boundaries_disallowed(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """check_tool_boundaries returns violations for disallowed tools."""
        calls = [
            ToolCall(name="Write"),  # not in allowed_tools
        ]
        violations = executor.check_tool_boundaries(sample_skill, calls)
        assert len(violations) == 1
        assert violations[0].tool_call.name == "Write"
        assert "Write" in violations[0].reason

    def test_check_tool_boundaries_with_arg_pattern(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """check_tool_boundaries checks argument patterns."""
        # The arg pattern "git:*" matches strings starting with "git:"
        # So "git commit" won't match (doesn't start with git:)
        # but "git:status" would match
        allowed_call = ToolCall(name="Bash", arguments={"command": "git:status"})
        disallowed_call = ToolCall(name="Bash", arguments={"command": "npm install"})
        violations_allowed = executor.check_tool_boundaries(sample_skill, [allowed_call])
        violations_disallowed = executor.check_tool_boundaries(sample_skill, [disallowed_call])
        assert violations_allowed == []
        assert len(violations_disallowed) == 1

    def test_check_tool_boundaries_uses_recorded_calls(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """check_tool_boundaries uses recorded calls when none provided."""
        executor.record_tool_call(ToolCall(name="Write"))
        violations = executor.check_tool_boundaries(sample_skill)
        assert len(violations) == 1

    def test_check_tool_boundaries_empty_allowed(self, executor: SkillExecutor) -> None:
        """check_tool_boundaries allows all when no allowed_tools."""
        skill = SkillDefinition(name="all", allowed_tools=[])
        violations = executor.check_tool_boundaries(skill, [ToolCall(name="Write")])
        assert violations == []

    def test_validate_execution_raises(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """validate_execution raises ToolBoundaryError on violation."""
        calls = [ToolCall(name="Write")]
        with pytest.raises(Exception):  # ToolBoundaryError
            executor.validate_execution(sample_skill, calls)

    def test_validate_execution_no_raise(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """validate_execution does not raise when all tools allowed."""
        calls = [ToolCall(name="Read")]
        executor.validate_execution(sample_skill, calls)  # no raise


class TestSkillExecutorExecute:
    """Tests for SkillExecutor.execute."""

    @pytest.mark.asyncio
    async def test_execute_with_prompt_callback(
        self, executor: SkillExecutor, sample_skill: SkillDefinition
    ) -> None:
        """execute returns content from get_prompt_for_command."""
        async def prompt_fn(args: str, ctx: ToolUseContext) -> list:
            return [{"type": "text", "text": f"Simplify: {args}"}]

        sample_skill.get_prompt_for_command = prompt_fn
        result = await executor.execute(sample_skill, {"skill_args": "main.py"}, ToolUseContext())
        assert result.skill_name == "simplify"
        assert len(result.content) == 1
        assert "Simplify: main.py" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_execute_without_callback(
        self, executor: SkillExecutor, sample_skill: SkillDefinition
    ) -> None:
        """execute returns instructions when no prompt callback."""
        sample_skill.instructions = "Review and simplify code."
        sample_skill._loaded = True
        result = await executor.execute(sample_skill, {}, ToolUseContext())
        assert result.skill_name == "simplify"
        assert len(result.content) == 1
        assert "simplify" in result.content[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_execute_tracks_duration(
        self, executor: SkillExecutor, sample_skill: SkillDefinition
    ) -> None:
        """execute records duration."""
        sample_skill.instructions = "Test"
        sample_skill._loaded = True
        result = await executor.execute(sample_skill, {}, ToolUseContext())
        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, executor: SkillExecutor) -> None:
        """execute returns error in result on exception."""

        async def bad_callback(args: str, ctx: ToolUseContext) -> list:
            msg: str = None  # type: ignore
            return msg.upper()  # type: ignore

        skill = SkillDefinition(name="bad", get_prompt_for_command=bad_callback)
        result = await executor.execute(skill, {}, ToolUseContext())
        assert result.error is not None


class TestSkillExecutorTimeout:
    """Tests for SkillExecutor timeout handling."""

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor: SkillExecutor, sample_skill: SkillDefinition) -> None:
        """execute_with_timeout completes within timeout."""
        sample_skill.instructions = "Test"
        sample_skill._loaded = True
        fast_exec = SkillExecutor(timeout=5.0)
        result = await fast_exec.execute_with_timeout(sample_skill, {}, ToolUseContext())
        assert result.skill_name == "simplify"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_slow_raises(self, executor: SkillExecutor) -> None:
        """execute_with_timeout raises on slow execution."""

        async def slow_callback(args: str, ctx: ToolUseContext) -> list:
            await asyncio.sleep(2)
            return [{"type": "text", "text": "done"}]

        skill = SkillDefinition(name="slow", get_prompt_for_command=slow_callback)
        short_exec = SkillExecutor(timeout=0.1)
        with pytest.raises(Exception):  # SkillTimeoutError
            await short_exec.execute_with_timeout(skill, {}, ToolUseContext())


class TestToolBoundaryViolation:
    """Tests for ToolBoundaryViolation dataclass."""

    def test_creation(self) -> None:
        """ToolBoundaryViolation stores violation details."""
        tc = ToolCall(name="Write", arguments={})
        violation = ToolBoundaryViolation(
            tool_call=tc,
            skill="test",
            allowed_tools=["Read"],
            reason="Write not allowed",
        )
        assert violation.tool_call.name == "Write"
        assert violation.skill == "test"
        assert "Read" in violation.allowed_tools


class TestCreateToolRestrictedContext:
    """Tests for create_tool_restricted_context helper."""

    def test_creates_new_context(self) -> None:
        """create_tool_restricted_context creates new context."""
        original = ToolUseContext(session_id="s1", cwd="/project")
        restricted = create_tool_restricted_context(original, ["Read"])
        assert restricted.session_id == "s1"
        assert restricted.cwd == "/project"


class TestGlobalExecutor:
    """Tests for global executor."""

    def test_get_global_executor_singleton(self) -> None:
        """get_global_executor returns the same instance."""
        exec1 = get_global_executor()
        exec2 = get_global_executor()
        assert exec1 is exec2


class TestToolCall:
    """Tests for ToolCall and ToolCallResult dataclasses."""

    def test_tool_call_defaults(self) -> None:
        """ToolCall has correct defaults."""
        tc = ToolCall(name="Read")
        assert tc.name == "Read"
        assert tc.arguments == {}
        assert tc.input_json == ""

    def test_tool_call_full(self) -> None:
        """ToolCall can be fully initialized."""
        tc = ToolCall(name="Bash", arguments={"command": "git status"}, input_json='{"command":"git status"}')
        assert tc.name == "Bash"
        assert tc.arguments["command"] == "git status"

    def test_tool_call_result_defaults(self) -> None:
        """ToolCallResult has correct defaults."""
        tc = ToolCall(name="Read")
        tr = ToolCallResult(tool_call=tc)
        assert tr.output == ""
        assert tr.error is None
        assert tr.success is True
