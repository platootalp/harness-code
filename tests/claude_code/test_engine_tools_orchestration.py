"""
Tests for ToolOrchestrator.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from claude_code.engine.tools.orchestration import (
    ExecutionPlan,
    ToolCall,
    ToolCallResult,
    ToolOrchestrator,
    ToolPartition,
)

# =============================================================================
# Mock Tool Implementations
# =============================================================================


class MockTool:
    """Mock tool for testing."""

    def __init__(
        self,
        name: str,
        concurrency_safe: bool = False,
        read_only: bool = False,
        execution_time: float = 0.0,
    ) -> None:
        self.name = name
        self._concurrency_safe = concurrency_safe
        self._read_only = read_only
        self._execution_time = execution_time

    def is_concurrency_safe(self, input: Any) -> bool:
        return self._concurrency_safe

    def is_read_only(self, input: Any) -> bool:
        return self._read_only

    async def call(
        self,
        args: Any,
        context: Any = None,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Any = None,
    ) -> Any:
        if self._execution_time > 0:
            await asyncio.sleep(self._execution_time)
        return {"status": "ok", "tool": self.name}


class MockContext:
    """Mock tool context."""
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def orchestrator() -> ToolOrchestrator:
    """Create an orchestrator for testing."""
    return ToolOrchestrator(max_parallel=5, timeout_per_tool=10.0)


@pytest.fixture
def mock_safe_tool() -> MockTool:
    """Create a concurrency-safe, read-only tool."""
    return MockTool("SafeTool", concurrency_safe=True, read_only=True)


@pytest.fixture
def mock_unsafe_tool() -> MockTool:
    """Create a non-concurrency-safe tool."""
    return MockTool("UnsafeTool", concurrency_safe=False, read_only=False)


@pytest.fixture
def mock_context() -> MockContext:
    """Create a mock context."""
    return MockContext()


# =============================================================================
# ToolCall Tests
# =============================================================================


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_creation(self, mock_safe_tool: MockTool, mock_context: MockContext) -> None:
        """ToolCall can be created with required fields."""
        async def mock_can_use(name: str) -> Any:
            return {"behavior": "allow"}

        call = ToolCall(
            tool=mock_safe_tool,
            args={"arg": "value"},
            tool_use_id="call-1",
            context=mock_context,
            can_use_tool=mock_can_use,
        )
        assert call.tool.name == "SafeTool"
        assert call.args == {"arg": "value"}
        assert call.tool_use_id == "call-1"


# =============================================================================
# ToolPartition Tests
# =============================================================================


class TestToolPartition:
    """Tests for ToolPartition dataclass."""

    def test_parallel_partition(self) -> None:
        """Parallel partition can be created."""
        partition = ToolPartition(execution_mode="parallel")
        assert partition.execution_mode == "parallel"
        assert partition.calls == []

    def test_serial_partition(self) -> None:
        """Serial partition can be created."""
        partition = ToolPartition(execution_mode="serial")
        assert partition.execution_mode == "serial"


# =============================================================================
# ExecutionPlan Tests
# =============================================================================


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""

    def test_empty_plan(self) -> None:
        """Empty plan has no calls."""
        plan = ExecutionPlan()
        assert plan.total_calls == 0
        assert not plan.has_parallel
        assert not plan.has_serial

    def test_plan_with_partitions(
        self,
        mock_safe_tool: MockTool,
        mock_unsafe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Plan tracks partitions correctly."""
        plan = ExecutionPlan(
            partitions=[
                ToolPartition(
                    calls=[
                        ToolCall(
                            tool=mock_safe_tool,
                            args={},
                            tool_use_id="1",
                            context=mock_context,
                            can_use_tool=lambda: None,
                        ),
                    ],
                    execution_mode="parallel",
                ),
                ToolPartition(
                    calls=[
                        ToolCall(
                            tool=mock_unsafe_tool,
                            args={},
                            tool_use_id="2",
                            context=mock_context,
                            can_use_tool=lambda: None,
                        ),
                    ],
                    execution_mode="serial",
                ),
            ]
        )
        assert plan.total_calls == 2
        assert plan.has_parallel
        assert plan.has_serial


# =============================================================================
# ToolOrchestrator.partition_tool_calls Tests
# =============================================================================


class TestPartitionToolCalls:
    """Tests for partition_tool_calls."""

    def test_empty_calls(self, orchestrator: ToolOrchestrator) -> None:
        """Empty calls produce empty plan."""
        plan = orchestrator.partition_tool_calls([])
        assert plan.total_calls == 0

    def test_single_safe_tool(
        self,
        orchestrator: ToolOrchestrator,
        mock_safe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Single safe tool goes in parallel partition."""
        calls = [
            ToolCall(
                tool=mock_safe_tool,
                args={},
                tool_use_id="1",
                context=mock_context,
                can_use_tool=lambda: None,
            )
        ]
        plan = orchestrator.partition_tool_calls(calls)
        assert plan.total_calls == 1
        assert plan.has_parallel
        assert not plan.has_serial
        assert len(plan.partitions) == 1
        assert plan.partitions[0].execution_mode == "parallel"

    def test_single_unsafe_tool(
        self,
        orchestrator: ToolOrchestrator,
        mock_unsafe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Single unsafe tool goes in serial partition."""
        calls = [
            ToolCall(
                tool=mock_unsafe_tool,
                args={},
                tool_use_id="1",
                context=mock_context,
                can_use_tool=lambda: None,
            )
        ]
        plan = orchestrator.partition_tool_calls(calls)
        assert plan.total_calls == 1
        assert not plan.has_parallel
        assert plan.has_serial
        assert len(plan.partitions) == 1
        assert plan.partitions[0].execution_mode == "serial"

    def test_mixed_tools_partitioned(
        self,
        orchestrator: ToolOrchestrator,
        mock_safe_tool: MockTool,
        mock_unsafe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Safe and unsafe tools are partitioned correctly."""
        calls = [
            ToolCall(
                tool=mock_safe_tool,
                args={},
                tool_use_id="1",
                context=mock_context,
                can_use_tool=lambda: None,
            ),
            ToolCall(
                tool=mock_unsafe_tool,
                args={},
                tool_use_id="2",
                context=mock_context,
                can_use_tool=lambda: None,
            ),
            ToolCall(
                tool=mock_safe_tool,
                args={},
                tool_use_id="3",
                context=mock_context,
                can_use_tool=lambda: None,
            ),
        ]
        plan = orchestrator.partition_tool_calls(calls)
        assert plan.total_calls == 3
        # Safe tools in parallel, unsafe in serial
        assert plan.has_parallel
        assert plan.has_serial
        # Should have: 1 parallel partition (for safe), 1 serial partition (for unsafe)
        assert len(plan.partitions) == 2
        assert plan.partitions[0].execution_mode == "parallel"
        assert plan.partitions[1].execution_mode == "serial"

    def test_max_parallel_split(
        self,
        orchestrator: ToolOrchestrator,
        mock_context: MockContext,
    ) -> None:
        """Tools are split into chunks at max_parallel boundary."""
        # Create orchestrator with max_parallel=2
        small_orchestrator = ToolOrchestrator(max_parallel=2)
        tools = [
            MockTool(f"Tool{i}", concurrency_safe=True, read_only=True)
            for i in range(5)
        ]
        calls = [
            ToolCall(
                tool=tool,
                args={},
                tool_use_id=str(i),
                context=mock_context,
                can_use_tool=lambda: None,
            )
            for i, tool in enumerate(tools)
        ]
        plan = small_orchestrator.partition_tool_calls(calls)
        assert plan.total_calls == 5
        # 5 tools with max_parallel=2: [2, 2, 1] = 3 partitions
        assert len(plan.partitions) == 3
        assert plan.partitions[0].execution_mode == "parallel"
        assert plan.partitions[1].execution_mode == "parallel"
        assert plan.partitions[2].execution_mode == "parallel"


# =============================================================================
# ToolOrchestrator.execute_parallel Tests
# =============================================================================


class TestExecuteParallel:
    """Tests for execute_parallel."""

    def test_empty_calls(self, orchestrator: ToolOrchestrator) -> None:
        """Empty calls return empty results."""
        results = asyncio.run(orchestrator.execute_parallel([]))
        assert results == []

    @pytest.mark.asyncio
    async def test_parallel_execution(
        self,
        orchestrator: ToolOrchestrator,
        mock_safe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Tools execute in parallel."""
        mock_safe_tool._execution_time = 0.05  # 50ms
        calls = [
            ToolCall(
                tool=mock_safe_tool,
                args={},
                tool_use_id=str(i),
                context=mock_context,
                can_use_tool=lambda: None,
            )
            for i in range(3)
        ]
        results = await orchestrator.execute_parallel(calls)
        assert len(results) == 3
        for r in results:
            assert r.error is None
            assert r.result is not None


# =============================================================================
# ToolOrchestrator.execute_serial Tests
# =============================================================================


class TestExecuteSerial:
    """Tests for execute_serial."""

    def test_empty_calls(self, orchestrator: ToolOrchestrator) -> None:
        """Empty calls return empty results."""
        results = asyncio.run(orchestrator.execute_serial([]))
        assert results == []

    @pytest.mark.asyncio
    async def test_serial_execution(
        self,
        orchestrator: ToolOrchestrator,
        mock_unsafe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Tools execute in order."""
        calls = [
            ToolCall(
                tool=mock_unsafe_tool,
                args={},
                tool_use_id=str(i),
                context=mock_context,
                can_use_tool=lambda: None,
            )
            for i in range(3)
        ]
        results = await orchestrator.execute_serial(calls)
        assert len(results) == 3
        for r in results:
            assert r.error is None
            assert r.result is not None


# =============================================================================
# ToolOrchestrator.execute_plan Tests
# =============================================================================


class TestExecutePlan:
    """Tests for execute_plan."""

    def test_empty_plan(self, orchestrator: ToolOrchestrator) -> None:
        """Empty plan returns empty results."""
        plan = ExecutionPlan()
        results = asyncio.run(orchestrator.execute_plan(plan))
        assert results == []

    @pytest.mark.asyncio
    async def test_plan_execution(
        self,
        orchestrator: ToolOrchestrator,
        mock_safe_tool: MockTool,
        mock_unsafe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Plan executes partitions in order."""
        plan = ExecutionPlan(
            partitions=[
                ToolPartition(
                    calls=[
                        ToolCall(
                            tool=mock_safe_tool,
                            args={},
                            tool_use_id="p1",
                            context=mock_context,
                            can_use_tool=lambda: None,
                        ),
                    ],
                    execution_mode="parallel",
                ),
                ToolPartition(
                    calls=[
                        ToolCall(
                            tool=mock_unsafe_tool,
                            args={},
                            tool_use_id="s1",
                            context=mock_context,
                            can_use_tool=lambda: None,
                        ),
                    ],
                    execution_mode="serial",
                ),
            ]
        )
        results = await orchestrator.execute_plan(plan)
        assert len(results) == 2
        assert results[0].tool_use_id == "p1"
        assert results[1].tool_use_id == "s1"


# =============================================================================
# ToolOrchestrator.execute Tests
# =============================================================================


class TestExecute:
    """Tests for the convenience execute method."""

    def test_empty_calls(self, orchestrator: ToolOrchestrator) -> None:
        """Empty calls return empty results."""
        results = asyncio.run(orchestrator.execute([]))
        assert results == []

    @pytest.mark.asyncio
    async def test_auto_partition_and_execute(
        self,
        orchestrator: ToolOrchestrator,
        mock_safe_tool: MockTool,
        mock_unsafe_tool: MockTool,
        mock_context: MockContext,
    ) -> None:
        """Execute auto-partitions and runs all calls."""
        calls = [
            ToolCall(
                tool=mock_safe_tool,
                args={},
                tool_use_id="1",
                context=mock_context,
                can_use_tool=lambda: None,
            ),
            ToolCall(
                tool=mock_unsafe_tool,
                args={},
                tool_use_id="2",
                context=mock_context,
                can_use_tool=lambda: None,
            ),
        ]
        results = await orchestrator.execute(calls)
        assert len(results) == 2
        assert results[0].tool_use_id == "1"
        assert results[1].tool_use_id == "2"
