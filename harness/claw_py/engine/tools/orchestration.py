"""
ToolOrchestrator - orchestrates tool execution with parallel/serial partitioning.

Partitions tool calls into concurrency-safe groups for parallel execution
and runs unsafe tools serially. Mirrors TypeScript tool orchestration patterns.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from claude_code.models.tool import (
        BaseTool,
        PermissionResult,
        ToolResult,
        ToolUseContext,
    )


@dataclass
class ToolCall:
    """A single tool call with its input and context."""

    tool: BaseTool
    args: dict[str, Any]
    tool_use_id: str
    context: ToolUseContext
    can_use_tool: Callable[..., Awaitable[PermissionResult]]
    parent_message: Any = None
    on_progress: Callable[..., None] | None = None


@dataclass
class ToolCallResult:
    """Result of a tool call execution."""

    tool_use_id: str
    result: ToolResult[Any] | None = None
    error: str | None = None
    permission_result: PermissionResult | None = None


@dataclass
class ToolPartition:
    """A partition of tool calls that can execute together."""

    calls: list[ToolCall] = field(default_factory=list)
    execution_mode: Literal["parallel", "serial"] = "parallel"


@dataclass
class ExecutionPlan:
    """Complete execution plan with partitioned tool calls."""

    partitions: list[ToolPartition] = field(default_factory=list)

    @property
    def total_calls(self) -> int:
        """Total number of tool calls in the plan."""
        return sum(len(p.calls) for p in self.partitions)

    @property
    def has_parallel(self) -> bool:
        """Whether any partition uses parallel execution."""
        return any(p.execution_mode == "parallel" for p in self.partitions)

    @property
    def has_serial(self) -> bool:
        """Whether any partition uses serial execution."""
        return any(p.execution_mode == "serial" for p in self.partitions)


class ToolOrchestrator:
    """
    Orchestrates tool execution with intelligent partitioning.

    Partitions tool calls into groups that can execute in parallel
    (concurrency-safe tools) and groups that must execute serially.
    Handles permission checking and error recovery.

    TypeScript equivalent: ToolOrchestrator or similar in engine/tools/
    """

    def __init__(
        self,
        max_parallel: int = 10,
        timeout_per_tool: float = 300.0,
    ) -> None:
        """
        Initialize the tool orchestrator.

        Args:
            max_parallel: Maximum number of tools to run in parallel.
            timeout_per_tool: Timeout for each individual tool call in seconds.
        """
        self._max_parallel = max_parallel
        self._timeout_per_tool = timeout_per_tool

    def partition_tool_calls(
        self,
        calls: Sequence[ToolCall],
    ) -> ExecutionPlan:
        """
        Partition tool calls into serial/parallel execution groups.

        Concurrency-safe tools (read-only, isConcurrencySafe returns True)
        are grouped for parallel execution. Tools that modify state or
        are not concurrency-safe are run serially.

        Args:
            calls: Sequence of tool calls to partition.

        Returns:
            ExecutionPlan with partitioned tool calls.

        Example:
            plan = orchestrator.partition_tool_calls([
                ToolCall(tool=file_read_tool, args={...}),
                ToolCall(tool=bash_tool, args={...}),
                ToolCall(tool=glob_tool, args={...}),
            ])
            # Returns plan with parallel group for [read, glob] and
            # serial group for [bash]
        """
        plan = ExecutionPlan()

        if not calls:
            return plan

        # Group 1: Concurrency-safe tools -> parallel
        safe_calls: list[ToolCall] = []
        # Group 2: Unsafe tools -> serial (but run serially among themselves)
        unsafe_calls: list[ToolCall] = []

        for call in calls:
            if self._is_concurrency_safe(call):
                safe_calls.append(call)
            else:
                unsafe_calls.append(call)

        # Create parallel partition for safe tools
        if safe_calls:
            # Further split if we exceed max_parallel
            for i in range(0, len(safe_calls), self._max_parallel):
                chunk = safe_calls[i : i + self._max_parallel]
                plan.partitions.append(
                    ToolPartition(calls=list(chunk), execution_mode="parallel")
                )

        # Create serial partitions for unsafe tools (each is its own serial step)
        # But group consecutive unsafe tools into one serial partition
        if unsafe_calls:
            plan.partitions.append(
                ToolPartition(calls=list(unsafe_calls), execution_mode="serial")
            )

        return plan

    def _is_concurrency_safe(self, call: ToolCall) -> bool:
        """Check if a tool call is safe for parallel execution."""
        safe = bool(call.tool.is_concurrency_safe(call.args))
        readonly = bool(call.tool.is_read_only(call.args))
        return safe and readonly

    async def execute_parallel(
        self,
        calls: Sequence[ToolCall],
    ) -> list[ToolCallResult]:
        """
        Execute multiple tool calls in parallel.

        Args:
            calls: Tool calls to execute in parallel.

        Returns:
            List of results in the same order as calls.
        """
        if not calls:
            return []

        async def execute_one(call: ToolCall) -> ToolCallResult:
            """Execute a single tool call with timeout."""
            try:
                result = await asyncio.wait_for(
                    call.tool.call(
                        args=call.args,
                        context=call.context,
                        can_use_tool=call.can_use_tool,
                        parent_message=call.parent_message,
                        on_progress=call.on_progress,
                    ),
                    timeout=self._timeout_per_tool,
                )
                return ToolCallResult(
                    tool_use_id=call.tool_use_id,
                    result=result,
                )
            except TimeoutError:
                return ToolCallResult(
                    tool_use_id=call.tool_use_id,
                    error=f"Tool execution timed out after {self._timeout_per_tool}s",
                )
            except Exception as e:  # noqa: BLE001
                return ToolCallResult(
                    tool_use_id=call.tool_use_id,
                    error=f"Tool execution failed: {e}",
                )

        results = await asyncio.gather(
            *[execute_one(call) for call in calls],
            return_exceptions=False,
        )
        return list(results)

    async def execute_serial(
        self,
        calls: Sequence[ToolCall],
    ) -> list[ToolCallResult]:
        """
        Execute multiple tool calls serially (in order).

        Args:
            calls: Tool calls to execute in order.

        Returns:
            List of results in the same order as calls.
        """
        if not calls:
            return []

        results: list[ToolCallResult] = []

        for call in calls:
            try:
                result = await asyncio.wait_for(
                    call.tool.call(
                        args=call.args,
                        context=call.context,
                        can_use_tool=call.can_use_tool,
                        parent_message=call.parent_message,
                        on_progress=call.on_progress,
                    ),
                    timeout=self._timeout_per_tool,
                )
                results.append(
                    ToolCallResult(
                        tool_use_id=call.tool_use_id,
                        result=result,
                    )
                )
            except TimeoutError:
                results.append(
                    ToolCallResult(
                        tool_use_id=call.tool_use_id,
                        error=f"Tool execution timed out after {self._timeout_per_tool}s",
                    )
                )
            except Exception as e:  # noqa: BLE001
                results.append(
                    ToolCallResult(
                        tool_use_id=call.tool_use_id,
                        error=f"Tool execution failed: {e}",
                    )
                )

        return results

    async def execute_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[ToolCallResult]:
        """
        Execute a complete tool execution plan.

        Executes partitions in order: parallel partitions first, then serial.
        Within each partition, tools execute according to their mode.

        Args:
            plan: The execution plan with partitioned tool calls.

        Returns:
            Flat list of results in order of execution.
        """
        all_results: list[ToolCallResult] = []

        for partition in plan.partitions:
            if partition.execution_mode == "parallel":
                results = await self.execute_parallel(partition.calls)
                all_results.extend(results)
            else:
                results = await self.execute_serial(partition.calls)
                all_results.extend(results)

        return all_results

    async def execute(
        self,
        calls: Sequence[ToolCall],
    ) -> list[ToolCallResult]:
        """
        Execute tool calls with automatic partitioning.

        Convenience method that partitions calls and executes the plan.
        Equivalent to:
            plan = partition_tool_calls(calls)
            return await execute_plan(plan)

        Args:
            calls: Tool calls to execute.

        Returns:
            List of results in the same order as calls.
        """
        plan = self.partition_tool_calls(calls)
        return await self.execute_plan(plan)
