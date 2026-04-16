"""
Tests for TaskStopTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.task_stop import TaskStopTool


@pytest.fixture
def task_stop_tool() -> TaskStopTool:
    return TaskStopTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    ctx.abort_controller = MagicMock()
    return ctx


@pytest.fixture
def mock_task() -> MagicMock:
    task = MagicMock()
    task.type = "background"
    task.description = "Background task"
    task.status = "running"
    return task


class TestTaskStopTool:
    """Tests for TaskStopTool."""

    def test_name(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.name == "TaskStop"

    def test_aliases(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.aliases == ["KillShell"]

    def test_search_hint(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.search_hint == "kill a running background task"

    def test_should_defer(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.should_defer is True

    def test_always_load(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.always_load is False

    def test_max_result_size_chars(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.max_result_size_chars == 100_000

    def test_strict(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.strict is False

    def test_description_text(self, task_stop_tool: TaskStopTool) -> None:
        assert "Stop" in task_stop_tool.description_text
        assert "task" in task_stop_tool.description_text.lower()

    def test_prompt_text(self, task_stop_tool: TaskStopTool) -> None:
        prompt = task_stop_tool.prompt_text
        assert "stop" in prompt.lower()

    def test_input_schema(self, task_stop_tool: TaskStopTool) -> None:
        schema = task_stop_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "task_id" in props
        assert "shell_id" in props
        assert schema["additionalProperties"] is False

    def test_output_schema(self, task_stop_tool: TaskStopTool) -> None:
        schema = task_stop_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "message" in props
        assert "task_id" in props
        assert "task_type" in props
        assert "command" in props

    def test_user_facing_name(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.user_facing_name() == "Stop Task"

    def test_is_enabled(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.is_enabled() is True

    def test_is_concurrency_safe(self, task_stop_tool: TaskStopTool) -> None:
        assert task_stop_tool.is_concurrency_safe({}) is True

    def test_render_tool_use_message(self, task_stop_tool: TaskStopTool) -> None:
        result = task_stop_tool.render_tool_use_message({})
        assert result is None

    def test_to_auto_classifier_input_task_id(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        result = task_stop_tool.to_auto_classifier_input({"task_id": "abc-123"})
        assert result == "abc-123"

    def test_to_auto_classifier_input_shell_id(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        result = task_stop_tool.to_auto_classifier_input({"shell_id": "shell-456"})
        assert result == "shell-456"

    def test_validate_input_missing_task_id(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        ctx = MagicMock()
        result = task_stop_tool.validate_input({}, ctx)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 1

    def test_validate_input_no_app_state(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        result = task_stop_tool.validate_input({"task_id": "task-1"}, ctx)
        assert result is not True
        assert isinstance(result, tuple)
        assert "Cannot access app state" in result[1]

    def test_validate_input_task_not_found(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        ctx = MagicMock()
        ctx.get_app_state = MagicMock(return_value=MagicMock(tasks={}))
        result = task_stop_tool.validate_input({"task_id": "nonexistent"}, ctx)
        assert result is not True
        assert isinstance(result, tuple)
        assert "No task found" in result[1]

    def test_validate_input_task_not_running(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        task = MagicMock()
        task.status = "completed"
        ctx = MagicMock()
        ctx.get_app_state = MagicMock(return_value=MagicMock(tasks={"task-1": task}))
        result = task_stop_tool.validate_input({"task_id": "task-1"}, ctx)
        assert result is not True
        assert isinstance(result, tuple)
        assert "not running" in result[1]
        assert result[2] == 3

    def test_validate_input_valid(
        self, task_stop_tool: TaskStopTool, mock_task: MagicMock
    ) -> None:
        ctx = MagicMock()
        ctx.get_app_state = MagicMock(return_value=MagicMock(tasks={"task-1": mock_task}))
        result = task_stop_tool.validate_input({"task_id": "task-1"}, ctx)
        assert result is True

    @pytest.mark.asyncio
    async def test_call_stops_task(
        self, task_stop_tool: TaskStopTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_stop_tool.call(
            {"task_id": "task-1"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "data" in result
        assert result["data"]["task_id"] == "task-1"
        assert result["data"]["task_type"] == "background"
        assert "Background task" in result["data"]["command"]

    @pytest.mark.asyncio
    async def test_call_task_not_found(
        self, task_stop_tool: TaskStopTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {}
        result = await task_stop_tool.call(
            {"task_id": "nonexistent"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "No task found" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_missing_task_id(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        ctx.set_app_state = None
        ctx.abort_controller = None
        with pytest.raises(ValueError, match="task_id"):
            await task_stop_tool.call({}, ctx, AsyncMock(), None)

    @pytest.mark.asyncio
    async def test_call_shell_id_alias(
        self, task_stop_tool: TaskStopTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"shell-1": mock_task}
        result = await task_stop_tool.call(
            {"shell_id": "shell-1"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["task_id"] == "shell-1"

    @pytest.mark.asyncio
    async def test_map_tool_result(
        self, task_stop_tool: TaskStopTool
    ) -> None:
        content = {
            "message": "Stopped task: task-1",
            "task_id": "task-1",
            "task_type": "background",
            "command": "sleep 10",
        }
        result = task_stop_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["type"] == "tool_result"
        assert "task-1" in result["content"]
