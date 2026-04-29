"""
Tests for TaskOutputTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.task_output import TaskOutputTool


@pytest.fixture
def task_output_tool() -> TaskOutputTool:
    return TaskOutputTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.abort_controller = None  # Avoid MagicMock truthy signal.aborted
    return ctx


@pytest.fixture
def mock_task() -> MagicMock:
    task = MagicMock()
    task.type = "background"
    task.status = "completed"
    task.description = "Background task"
    task.output = "Task output here"
    task.exit_code = 0
    task.error = None
    return task


class TestTaskOutputTool:
    """Tests for TaskOutputTool."""

    def test_name(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.name == "TaskOutput"

    def test_aliases(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.aliases == ["AgentOutputTool", "BashOutputTool"]

    def test_search_hint(self, task_output_tool: TaskOutputTool) -> None:
        assert "output" in task_output_tool.search_hint.lower()
        assert "background task" in task_output_tool.search_hint

    def test_should_defer(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.should_defer is True

    def test_always_load(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.always_load is False

    def test_max_result_size_chars(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.max_result_size_chars == 100_000

    def test_strict(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.strict is False

    def test_description_text(self, task_output_tool: TaskOutputTool) -> None:
        assert "output" in task_output_tool.description_text.lower()

    def test_prompt_text(self, task_output_tool: TaskOutputTool) -> None:
        prompt = task_output_tool.prompt_text
        assert "output" in prompt.lower()
        assert "block" in prompt.lower()

    def test_input_schema(self, task_output_tool: TaskOutputTool) -> None:
        schema = task_output_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "task_id" in props
        assert "block" in props
        assert "timeout" in props
        assert "task_id" in schema["required"]
        assert schema["additionalProperties"] is False

    def test_output_schema(self, task_output_tool: TaskOutputTool) -> None:
        schema = task_output_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "retrieval_status" in props
        assert props["retrieval_status"]["enum"] == ["success", "timeout", "not_ready"]
        assert "task" in props
        task_props = schema["properties"]["task"]["properties"]
        assert "task_id" in task_props
        assert "task_type" in task_props
        assert "status" in task_props
        assert "description" in task_props
        assert "output" in task_props
        assert "exitCode" in task_props
        assert "error" in task_props

    def test_user_facing_name(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.user_facing_name() == "Task Output"

    def test_is_enabled(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.is_enabled() is True

    def test_is_concurrency_safe(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, task_output_tool: TaskOutputTool) -> None:
        assert task_output_tool.is_read_only({}) is True

    def test_render_tool_use_message(self, task_output_tool: TaskOutputTool) -> None:
        result = task_output_tool.render_tool_use_message({})
        assert result is None

    def test_to_auto_classifier_input(self, task_output_tool: TaskOutputTool) -> None:
        result = task_output_tool.to_auto_classifier_input({"task_id": "abc-123"})
        assert result == "abc-123"

    def test_to_auto_classifier_input_empty(self, task_output_tool: TaskOutputTool) -> None:
        result = task_output_tool.to_auto_classifier_input({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_call_returns_output(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_output_tool.call(
            {"task_id": "task-1"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "data" in result
        assert result["data"]["task"] is not None
        assert result["data"]["task"]["task_id"] == "task-1"
        assert result["data"]["task"]["task_type"] == "background"
        assert result["data"]["task"]["status"] == "completed"
        assert result["data"]["task"]["output"] == "Task output here"
        assert result["data"]["task"]["exitCode"] == 0
        assert result["data"]["retrieval_status"] == "success"

    @pytest.mark.asyncio
    async def test_call_task_not_found(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {}
        result = await task_output_tool.call(
            {"task_id": "nonexistent"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["task"] is None
        assert result["data"]["retrieval_status"] == "success"

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, task_output_tool: TaskOutputTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        result = await task_output_tool.call(
            {"task_id": "task-1"},
            ctx,
            AsyncMock(),
            None,
        )
        assert result["data"]["task"] is None

    @pytest.mark.asyncio
    async def test_call_missing_task_id(self, task_output_tool: TaskOutputTool) -> None:
        ctx = MagicMock()
        with pytest.raises(ValueError, match="task_id"):
            await task_output_tool.call({}, ctx, AsyncMock(), None)

    @pytest.mark.asyncio
    async def test_call_non_blocking_completed(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_output_tool.call(
            {"task_id": "task-1", "block": False},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["retrieval_status"] == "success"
        assert result["data"]["task"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_call_non_blocking_running(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock
    ) -> None:
        running_task = MagicMock()
        running_task.type = "background"
        running_task.status = "running"
        running_task.description = "Running..."
        running_task.output = ""
        running_task.exit_code = None
        running_task.error = None
        mock_context.get_app_state.return_value.tasks = {"task-1": running_task}
        result = await task_output_tool.call(
            {"task_id": "task-1", "block": False},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["retrieval_status"] == "not_ready"
        assert result["data"]["task"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_call_non_blocking_pending(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock
    ) -> None:
        pending_task = MagicMock()
        pending_task.type = "background"
        pending_task.status = "pending"
        pending_task.description = "Pending..."
        pending_task.output = ""
        pending_task.exit_code = None
        pending_task.error = None
        mock_context.get_app_state.return_value.tasks = {"task-1": pending_task}
        result = await task_output_tool.call(
            {"task_id": "task-1", "block": False},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["retrieval_status"] == "not_ready"

    @pytest.mark.asyncio
    async def test_call_with_error(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock
    ) -> None:
        failed_task = MagicMock()
        failed_task.type = "background"
        failed_task.status = "failed"
        failed_task.description = "Failed task"
        failed_task.output = ""
        failed_task.exit_code = 1
        failed_task.error = "Something went wrong"
        mock_context.get_app_state.return_value.tasks = {"task-1": failed_task}
        result = await task_output_tool.call(
            {"task_id": "task-1"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["retrieval_status"] == "success"
        assert result["data"]["task"]["status"] == "failed"
        assert result["data"]["task"]["error"] == "Something went wrong"
        assert result["data"]["task"]["exitCode"] == 1

    @pytest.mark.asyncio
    async def test_call_output_none_returns_empty_string(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock
    ) -> None:
        task = MagicMock()
        task.type = "background"
        task.status = "completed"
        task.description = "Test"
        task.output = None
        task.exit_code = 0
        task.error = None
        mock_context.get_app_state.return_value.tasks = {"task-1": task}
        result = await task_output_tool.call(
            {"task_id": "task-1"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["task"]["output"] == "None"

    @pytest.mark.asyncio
    async def test_call_custom_timeout(
        self, task_output_tool: TaskOutputTool, mock_context: MagicMock
    ) -> None:
        pending_task = MagicMock()
        pending_task.type = "background"
        pending_task.status = "running"
        pending_task.description = "Running..."
        pending_task.output = ""
        pending_task.exit_code = None
        pending_task.error = None
        # Return fresh app state each time get_app_state is called
        mock_context.get_app_state = MagicMock(return_value=MagicMock(
            tasks={"task-1": pending_task}
        ))
        result = await task_output_tool.call(
            {"task_id": "task-1", "block": True, "timeout": 50},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["retrieval_status"] == "timeout"

    @pytest.mark.asyncio
    async def test_map_tool_result_not_found(
        self, task_output_tool: TaskOutputTool
    ) -> None:
        result = task_output_tool.map_tool_result_to_tool_result_block_param(
            {"task": None}, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["content"] == "Task not found"

    @pytest.mark.asyncio
    async def test_map_tool_result_timeout(
        self, task_output_tool: TaskOutputTool
    ) -> None:
        content = {
            "retrieval_status": "timeout",
            "task": {"status": "running"},
        }
        result = task_output_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert "timed out" in result["content"].lower()
        assert "running" in result["content"]

    @pytest.mark.asyncio
    async def test_map_tool_result_not_ready(
        self, task_output_tool: TaskOutputTool
    ) -> None:
        content = {
            "retrieval_status": "not_ready",
            "task": {"status": "pending"},
        }
        result = task_output_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert "still running" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_map_tool_result_success(
        self, task_output_tool: TaskOutputTool
    ) -> None:
        content = {
            "retrieval_status": "success",
            "task": {"output": "Hello, World!"},
        }
        result = task_output_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["content"] == "Hello, World!"
