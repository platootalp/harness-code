"""
Tests for TaskCreateTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.task_create import (
    TaskCreateTool,
    TaskCreateToolOutput,
    TaskOutput,
)


@pytest.fixture
def task_create_tool() -> TaskCreateTool:
    return TaskCreateTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


class TestTaskCreateTool:
    """Tests for TaskCreateTool."""

    def test_name(self, task_create_tool: TaskCreateTool) -> None:
        assert task_create_tool.name == "TaskCreate"

    def test_input_schema(self, task_create_tool: TaskCreateTool) -> None:
        schema = task_create_tool.input_schema
        assert schema["type"] == "object"
        assert "subject" in schema["required"]
        assert "description" in schema["required"]
        assert "subject" in schema["properties"]
        assert "description" in schema["properties"]
        assert "activeForm" in schema["properties"]
        assert "metadata" in schema["properties"]

    def test_is_concurrency_safe(self, task_create_tool: TaskCreateTool) -> None:
        assert task_create_tool.is_concurrency_safe({}) is True

    def test_should_defer(self, task_create_tool: TaskCreateTool) -> None:
        assert task_create_tool.should_defer is True

    def test_max_result_size_chars(self, task_create_tool: TaskCreateTool) -> None:
        assert task_create_tool.max_result_size_chars == 100_000

    def test_to_auto_classifier_input(self, task_create_tool: TaskCreateTool) -> None:
        result = task_create_tool.to_auto_classifier_input(
            {"subject": "Fix bug"}
        )
        assert result == "Fix bug"

    @pytest.mark.asyncio
    async def test_validate_input_missing_subject(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.validate_input(
            {"description": "desc"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_missing_description(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.validate_input(
            {"subject": "Fix bug"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_subject_too_long(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.validate_input(
            {"subject": "x" * 201, "description": "desc"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_valid(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.validate_input(
            {"subject": "Fix bug", "description": "Fix the bug"}, mock_context
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_creates_task(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.call(
            {"subject": "Fix bug", "description": "Fix the bug"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, TaskCreateToolOutput)
        assert result.data.task.subject == "Fix bug"
        assert len(result.data.task.id) == 8

    @pytest.mark.asyncio
    async def test_call_generates_unique_ids(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result1 = await task_create_tool.call(
            {"subject": "Task 1", "description": "desc1"},
            mock_context,
            AsyncMock(),
            None,
        )
        result2 = await task_create_tool.call(
            {"subject": "Task 2", "description": "desc2"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result1.data.task.id != result2.data.task.id

    @pytest.mark.asyncio
    async def test_call_with_active_form(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.call(
            {
                "subject": "Fix bug",
                "description": "Fix the bug",
                "activeForm": "Fixing bug",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.task.subject == "Fix bug"

    @pytest.mark.asyncio
    async def test_call_with_metadata(
        self, task_create_tool: TaskCreateTool, mock_context: MagicMock
    ) -> None:
        result = await task_create_tool.call(
            {
                "subject": "Fix bug",
                "description": "Fix the bug",
                "metadata": {"priority": "high"},
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.task.subject == "Fix bug"

    @pytest.mark.asyncio
    async def test_description(self, task_create_tool: TaskCreateTool) -> None:
        desc = await task_create_tool.description(
            {"subject": "Fix bug"}, {}
        )
        assert "Fix bug" in desc

    @pytest.mark.asyncio
    async def test_description_empty_input(
        self, task_create_tool: TaskCreateTool
    ) -> None:
        desc = await task_create_tool.description({}, {})
        assert "Create" in desc

    @pytest.mark.asyncio
    async def test_prompt(self, task_create_tool: TaskCreateTool) -> None:
        prompt = await task_create_tool.prompt({})
        assert "TaskCreate" in prompt or "task" in prompt.lower()


class TestTaskOutput:
    """Tests for TaskOutput dataclass."""

    def test_task_output_creation(self) -> None:
        task = TaskOutput(id="123", subject="Test task")
        assert task.id == "123"
        assert task.subject == "Test task"


class TestTaskCreateToolOutput:
    """Tests for TaskCreateToolOutput dataclass."""

    def test_output_creation(self) -> None:
        task = TaskOutput(id="abc", subject="My task")
        output = TaskCreateToolOutput(task=task)
        assert output.task.id == "abc"
        assert output.task.subject == "My task"
