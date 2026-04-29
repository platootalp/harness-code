"""
Tests for TaskListTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.task_list import TaskListTool


@pytest.fixture
def task_list_tool() -> TaskListTool:
    return TaskListTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    return ctx


@pytest.fixture
def mock_task() -> MagicMock:
    task = MagicMock()
    task.id = "task-1"
    task.subject = "First task"
    task.status = "pending"
    task.owner = None
    task.blockedBy = []
    task.metadata = {}
    return task


class TestTaskListTool:
    """Tests for TaskListTool."""

    def test_name(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.name == "TaskList"

    def test_aliases(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.aliases is None

    def test_search_hint(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.search_hint == "list all tasks"

    def test_should_defer(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.should_defer is True

    def test_always_load(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.always_load is False

    def test_max_result_size_chars(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.max_result_size_chars == 100_000

    def test_strict(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.strict is False

    def test_description_text(self, task_list_tool: TaskListTool) -> None:
        assert "List" in task_list_tool.description_text
        assert "task" in task_list_tool.description_text.lower()

    def test_prompt_text(self, task_list_tool: TaskListTool) -> None:
        prompt = task_list_tool.prompt_text
        assert "task" in prompt.lower()

    def test_input_schema(self, task_list_tool: TaskListTool) -> None:
        schema = task_list_tool.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["additionalProperties"] is False

    def test_output_schema(self, task_list_tool: TaskListTool) -> None:
        schema = task_list_tool.output_schema
        assert schema["type"] == "object"
        assert "tasks" in schema["properties"]
        items = schema["properties"]["tasks"]["items"]["properties"]
        assert "id" in items
        assert "subject" in items
        assert "status" in items
        assert "owner" in items
        assert "blockedBy" in items

    def test_user_facing_name(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.user_facing_name() == "TaskList"

    def test_is_enabled(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.is_enabled() is True

    def test_is_concurrency_safe(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, task_list_tool: TaskListTool) -> None:
        assert task_list_tool.is_read_only({}) is True

    def test_render_tool_use_message(self, task_list_tool: TaskListTool) -> None:
        result = task_list_tool.render_tool_use_message({})
        assert result is None

    @pytest.mark.asyncio
    async def test_call_returns_tasks(
        self, task_list_tool: TaskListTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        task2 = MagicMock()
        task2.id = "task-2"
        task2.subject = "Second task"
        task2.status = "in_progress"
        task2.owner = "dev-1"
        task2.blockedBy = []
        task2.metadata = {}

        mock_context.get_app_state.return_value.tasks = {
            "task-1": mock_task,
            "task-2": task2,
        }
        result = await task_list_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "data" in result
        assert "tasks" in result["data"]
        assert len(result["data"]["tasks"]) == 2

    @pytest.mark.asyncio
    async def test_call_excludes_internal_tasks(
        self, task_list_tool: TaskListTool, mock_context: MagicMock
    ) -> None:
        regular_task = MagicMock()
        regular_task.id = "task-1"
        regular_task.subject = "Regular"
        regular_task.status = "pending"
        regular_task.owner = None
        regular_task.blockedBy = []
        regular_task.metadata = {}

        internal_task = MagicMock()
        internal_task.id = "internal-1"
        internal_task.subject = "Internal"
        internal_task.status = "pending"
        internal_task.owner = None
        internal_task.blockedBy = []
        internal_task.metadata = {"_internal": True}

        mock_context.get_app_state.return_value.tasks = {
            "task-1": regular_task,
            "internal-1": internal_task,
        }
        result = await task_list_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        ids = [t["id"] for t in result["data"]["tasks"]]
        assert "task-1" in ids
        assert "internal-1" not in ids

    @pytest.mark.asyncio
    async def test_call_filters_resolved_blockers(
        self, task_list_tool: TaskListTool, mock_context: MagicMock
    ) -> None:
        completed_task = MagicMock()
        completed_task.id = "P1-1"
        completed_task.subject = "Completed"
        completed_task.status = "completed"
        completed_task.owner = None
        completed_task.blockedBy = []
        completed_task.metadata = {}

        blocked_task = MagicMock()
        blocked_task.id = "task-2"
        blocked_task.subject = "Blocked"
        blocked_task.status = "pending"
        blocked_task.owner = None
        blocked_task.blockedBy = ["P1-1", "P1-2"]
        blocked_task.metadata = {}

        pending_blocker = MagicMock()
        pending_blocker.id = "P1-2"
        pending_blocker.subject = "Pending"
        pending_blocker.status = "in_progress"
        pending_blocker.owner = None
        pending_blocker.blockedBy = []
        pending_blocker.metadata = {}

        mock_context.get_app_state.return_value.tasks = {
            "P1-1": completed_task,
            "task-2": blocked_task,
            "P1-2": pending_blocker,
        }
        result = await task_list_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        task_2 = next(t for t in result["data"]["tasks"] if t["id"] == "task-2")
        assert "P1-1" not in task_2["blockedBy"]
        assert "P1-2" in task_2["blockedBy"]

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, task_list_tool: TaskListTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        result = await task_list_tool.call({}, ctx, AsyncMock(), None)
        assert result["data"]["tasks"] == []

    @pytest.mark.asyncio
    async def test_call_empty_tasks(self, task_list_tool: TaskListTool, mock_context: MagicMock) -> None:
        mock_context.get_app_state.return_value.tasks = {}
        result = await task_list_tool.call({}, mock_context, AsyncMock(), None)
        assert result["data"]["tasks"] == []

    @pytest.mark.asyncio
    async def test_map_tool_result_empty(
        self, task_list_tool: TaskListTool
    ) -> None:
        result = task_list_tool.map_tool_result_to_tool_result_block_param(
            {"tasks": []}, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["type"] == "tool_result"
        assert result["content"] == "No tasks found"

    @pytest.mark.asyncio
    async def test_map_tool_result_with_tasks(
        self, task_list_tool: TaskListTool
    ) -> None:
        content = {
            "tasks": [
                {
                    "id": "task-1",
                    "subject": "First task",
                    "status": "pending",
                    "owner": "dev-1",
                    "blockedBy": [],
                },
                {
                    "id": "task-2",
                    "subject": "Second task",
                    "status": "in_progress",
                    "owner": None,
                    "blockedBy": ["P1-1"],
                },
            ]
        }
        result = task_list_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-2"
        )
        assert result["tool_use_id"] == "tool-use-2"
        assert "task-1" in result["content"]
        assert "First task" in result["content"]
        assert "dev-1" in result["content"]
        assert "task-2" in result["content"]
        assert "Second task" in result["content"]
        assert "P1-1" in result["content"]
