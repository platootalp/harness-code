"""
Tests for TaskUpdateTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.task_update import TaskUpdateTool


@pytest.fixture
def task_update_tool() -> TaskUpdateTool:
    return TaskUpdateTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


@pytest.fixture
def mock_task() -> MagicMock:
    task = MagicMock()
    task.subject = "Original subject"
    task.description = "Original description"
    task.activeForm = ""
    task.owner = None
    task.status = "pending"
    task.metadata = {}
    return task


class TestTaskUpdateTool:
    """Tests for TaskUpdateTool."""

    def test_name(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.name == "TaskUpdate"

    def test_aliases(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.aliases is None

    def test_search_hint(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.search_hint == "update a task"

    def test_should_defer(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.should_defer is True

    def test_always_load(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.always_load is False

    def test_max_result_size_chars(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.max_result_size_chars == 100_000

    def test_strict(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.strict is False

    def test_description_text(self, task_update_tool: TaskUpdateTool) -> None:
        assert "Update" in task_update_tool.description_text
        assert "task" in task_update_tool.description_text.lower()

    def test_prompt_text(self, task_update_tool: TaskUpdateTool) -> None:
        prompt = task_update_tool.prompt_text
        assert "update" in prompt.lower()

    def test_input_schema(self, task_update_tool: TaskUpdateTool) -> None:
        schema = task_update_tool.input_schema
        assert schema["type"] == "object"
        assert "taskId" in schema["required"]
        props = schema["properties"]
        assert "taskId" in props
        assert "subject" in props
        assert "description" in props
        assert "activeForm" in props
        assert "status" in props
        assert "addBlocks" in props
        assert "addBlockedBy" in props
        assert "owner" in props
        assert "metadata" in props

    def test_output_schema(self, task_update_tool: TaskUpdateTool) -> None:
        schema = task_update_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "success" in props
        assert "taskId" in props
        assert "updatedFields" in props
        assert "error" in props
        assert "statusChange" in props

    def test_user_facing_name(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.user_facing_name() == "TaskUpdate"

    def test_is_enabled(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.is_enabled() is True

    def test_is_concurrency_safe(self, task_update_tool: TaskUpdateTool) -> None:
        assert task_update_tool.is_concurrency_safe({}) is True

    def test_render_tool_use_message(self, task_update_tool: TaskUpdateTool) -> None:
        result = task_update_tool.render_tool_use_message({})
        assert result is None

    def test_to_auto_classifier_input(self, task_update_tool: TaskUpdateTool) -> None:
        result = task_update_tool.to_auto_classifier_input(
            {"taskId": "abc", "status": "completed", "subject": "Fix bug"}
        )
        assert "abc" in result
        assert "completed" in result
        assert "Fix bug" in result

    def test_to_auto_classifier_input_empty(self, task_update_tool: TaskUpdateTool) -> None:
        result = task_update_tool.to_auto_classifier_input({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_call_updates_subject(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "subject": "New subject"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert result["data"]["taskId"] == "task-1"
        assert "subject" in result["data"]["updatedFields"]

    @pytest.mark.asyncio
    async def test_call_updates_description(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "description": "New description"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "description" in result["data"]["updatedFields"]

    @pytest.mark.asyncio
    async def test_call_updates_active_form(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "activeForm": "Updating..."},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "activeForm" in result["data"]["updatedFields"]

    @pytest.mark.asyncio
    async def test_call_updates_owner(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "owner": "dev-1"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "owner" in result["data"]["updatedFields"]

    @pytest.mark.asyncio
    async def test_call_updates_status(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "status": "completed"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "status" in result["data"]["updatedFields"]
        assert result["data"]["statusChange"]["from"] == "pending"
        assert result["data"]["statusChange"]["to"] == "completed"

    @pytest.mark.asyncio
    async def test_call_updates_metadata(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "metadata": {"priority": "high"}},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "metadata" in result["data"]["updatedFields"]

    @pytest.mark.asyncio
    async def test_call_metadata_null_removes_key(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_task.metadata = {"priority": "high", "tag": "vip"}
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "metadata": {"priority": None}},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_call_deletes_task(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "status": "deleted"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert "deleted" in result["data"]["updatedFields"]
        assert result["data"]["statusChange"]["to"] == "deleted"

    @pytest.mark.asyncio
    async def test_call_task_not_found(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.tasks = {}
        result = await task_update_tool.call(
            {"taskId": "nonexistent"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is False
        assert result["data"]["error"] == "Task not found"

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, task_update_tool: TaskUpdateTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        ctx.set_app_state = None
        result = await task_update_tool.call(
            {"taskId": "task-1"},
            ctx,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is False
        assert result["data"]["error"] == "Cannot access app state"

    @pytest.mark.asyncio
    async def test_call_no_changes(
        self, task_update_tool: TaskUpdateTool, mock_context: MagicMock, mock_task: MagicMock
    ) -> None:
        mock_task.subject = "Same subject"
        mock_context.get_app_state.return_value.tasks = {"task-1": mock_task}
        result = await task_update_tool.call(
            {"taskId": "task-1", "subject": "Same subject"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["success"] is True
        assert result["data"]["updatedFields"] == []

    @pytest.mark.asyncio
    async def test_map_tool_result_failure(
        self, task_update_tool: TaskUpdateTool
    ) -> None:
        content = {
            "success": False,
            "taskId": "task-1",
            "error": "Task not found",
            "updatedFields": [],
        }
        result = task_update_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["content"] == "Task not found"

    @pytest.mark.asyncio
    async def test_map_tool_result_success(
        self, task_update_tool: TaskUpdateTool
    ) -> None:
        content = {
            "success": True,
            "taskId": "task-1",
            "updatedFields": ["subject", "status"],
            "statusChange": {"from": "pending", "to": "completed"},
        }
        result = task_update_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert "Updated task #task-1" in result["content"]
        assert "subject" in result["content"]
        assert "status" in result["content"]
        assert "Task completed" in result["content"]

    @pytest.mark.asyncio
    async def test_map_tool_result_verification_nudge(
        self, task_update_tool: TaskUpdateTool
    ) -> None:
        content = {
            "success": True,
            "taskId": "task-1",
            "updatedFields": ["status"],
            "statusChange": {"from": "pending", "to": "completed"},
            "verificationNudgeNeeded": True,
        }
        result = task_update_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert "verification" in result["content"].lower()
