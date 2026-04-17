"""
Tests for TaskGetTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.task_get import TaskGetTool


@pytest.fixture
def task_get_tool() -> TaskGetTool:
    return TaskGetTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    return ctx


@pytest.fixture
def mock_task() -> MagicMock:
    task = MagicMock()
    task.id = "test-123"
    task.subject = "Test task"
    task.description = "Test description"
    task.status = "pending"
    task.blocks = []
    task.blockedBy = ["P1-1", "P1-2"]
    return task


class TestTaskGetTool:
    """Tests for TaskGetTool."""

    def test_name(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.name == "TaskGet"

    def test_aliases(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.aliases is None

    def test_search_hint(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.search_hint == "retrieve a task by ID"

    def test_should_defer(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.should_defer is True

    def test_always_load(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.always_load is False

    def test_max_result_size_chars(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.max_result_size_chars == 100_000

    def test_strict(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.strict is False

    def test_description_text(self, task_get_tool: TaskGetTool) -> None:
        assert "Retrieve" in task_get_tool.description_text
        assert "task" in task_get_tool.description_text.lower()

    def test_prompt_text(self, task_get_tool: TaskGetTool) -> None:
        prompt = task_get_tool.prompt_text
        assert "task" in prompt.lower()
        assert "ID" in prompt

    def test_input_schema(self, task_get_tool: TaskGetTool) -> None:
        schema = task_get_tool.input_schema
        assert schema["type"] == "object"
        assert "taskId" in schema["required"]
        assert "taskId" in schema["properties"]
        assert schema["additionalProperties"] is False

    def test_output_schema(self, task_get_tool: TaskGetTool) -> None:
        schema = task_get_tool.output_schema
        assert schema["type"] == "object"
        assert "task" in schema["properties"]
        task_props = schema["properties"]["task"]["properties"]
        assert "id" in task_props
        assert "subject" in task_props
        assert "description" in task_props
        assert "status" in task_props
        assert "blocks" in task_props
        assert "blockedBy" in task_props

    def test_user_facing_name(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.user_facing_name() == "TaskGet"

    def test_is_enabled(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.is_enabled() is True

    def test_is_concurrency_safe(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, task_get_tool: TaskGetTool) -> None:
        assert task_get_tool.is_read_only({}) is True

    def test_render_tool_use_message(self, task_get_tool: TaskGetTool) -> None:
        result = task_get_tool.render_tool_use_message({})
        assert result is None


    @pytest.mark.asyncio
    async def test_call_returns_task(
        self, task_get_tool: TaskGetTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"test-123": mock_task}
        result = await task_get_tool.call(
            {"taskId": "test-123"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "data" in result
        assert result["data"]["task"] is not None
        assert result["data"]["task"]["id"] == "test-123"
        assert result["data"]["task"]["subject"] == "Test task"
        assert result["data"]["task"]["description"] == "Test description"
        assert result["data"]["task"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_call_task_not_found(
        self, task_get_tool: TaskGetTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {}
        result = await task_get_tool.call(
            {"taskId": "nonexistent"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["task"] is None

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, task_get_tool: TaskGetTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        result = await task_get_tool.call(
            {"taskId": "test-123"},
            ctx,
            AsyncMock(),
            None,
        )
        assert result["data"]["task"] is None

    @pytest.mark.asyncio
    async def test_call_with_blocks(
        self, task_get_tool: TaskGetTool, mock_context: MagicMock
    ) -> None:
        task = MagicMock()
        task.id = "blocker-task"
        task.subject = "Blocker"
        task.description = "Blocks other tasks"
        task.status = "in_progress"
        task.blocks = ["task-2", "task-3"]
        task.blockedBy = []
        mock_context.get_app_state.return_value.tasks = {"blocker-task": task}

        result = await task_get_tool.call(
            {"taskId": "blocker-task"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["task"]["blocks"] == ["task-2", "task-3"]
        assert result["data"]["task"]["blockedBy"] == []

    @pytest.mark.asyncio
    async def test_map_tool_result_to_tool_result_block_param_not_found(
        self, task_get_tool: TaskGetTool
    ) -> None:
        result = task_get_tool.map_tool_result_to_tool_result_block_param(
            {"task": None}, "tool-use-123"
        )
        assert result["tool_use_id"] == "tool-use-123"
        assert result["type"] == "tool_result"
        assert result["content"] == "Task not found"

    @pytest.mark.asyncio
    async def test_map_tool_result_to_tool_result_block_param_found(
        self, task_get_tool: TaskGetTool
    ) -> None:
        content = {
            "task": {
                "id": "test-456",
                "subject": "My Task",
                "description": "Task description",
                "status": "completed",
                "blockedBy": ["P1-1"],
                "blocks": [],
            }
        }
        result = task_get_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-456"
        )
        assert result["tool_use_id"] == "tool-use-456"
        assert result["type"] == "tool_result"
        assert "Task #test-456" in result["content"]
        assert "My Task" in result["content"]
        assert "completed" in result["content"]
        assert "P1-1" in result["content"]

    @pytest.mark.asyncio
    async def test_map_tool_result_blocks(
        self, task_get_tool: TaskGetTool
    ) -> None:
        content = {
            "task": {
                "id": "task-1",
                "subject": "Blocker",
                "description": "desc",
                "status": "pending",
                "blockedBy": [],
                "blocks": ["task-2", "task-3"],
            }
        }
        result = task_get_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert "Blocks:" in result["content"]
        assert "task-2" in result["content"]
        assert "task-3" in result["content"]
