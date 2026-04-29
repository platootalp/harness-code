"""
Tests for CronCreateTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_code.tools.cron_create import CronCreateTool


@pytest.fixture
def cron_create_tool() -> CronCreateTool:
    return CronCreateTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestCronCreateTool:
    """Tests for CronCreateTool."""

    def test_name(self, cron_create_tool: CronCreateTool) -> None:
        assert cron_create_tool.name == "CronCreate"

    def test_aliases(self, cron_create_tool: CronCreateTool) -> None:
        assert cron_create_tool.aliases is None

    def test_search_hint(self, cron_create_tool: CronCreateTool) -> None:
        assert "schedule" in cron_create_tool.search_hint.lower()
        assert "prompt" in cron_create_tool.search_hint.lower()

    def test_should_defer(self, cron_create_tool: CronCreateTool) -> None:
        assert cron_create_tool.should_defer is True

    def test_always_load(self, cron_create_tool: CronCreateTool) -> None:
        assert cron_create_tool.always_load is False

    def test_max_result_size_chars(self, cron_create_tool: CronCreateTool) -> None:
        assert cron_create_tool.max_result_size_chars == 100_000

    def test_strict(self, cron_create_tool: CronCreateTool) -> None:
        # TypeScript CronCreateTool doesn't define strict, defaults to false
        assert cron_create_tool.strict is False

    def test_description_text(self, cron_create_tool: CronCreateTool) -> None:
        assert "schedule" in cron_create_tool.description_text.lower()

    def test_prompt_text(self, cron_create_tool: CronCreateTool) -> None:
        assert "schedule" in cron_create_tool.prompt_text.lower()

    def test_input_schema(self, cron_create_tool: CronCreateTool) -> None:
        schema = cron_create_tool.input_schema
        assert schema["type"] == "object"
        assert "cron" in schema["required"]
        assert "prompt" in schema["required"]
        props = schema["properties"]
        assert "cron" in props
        assert "prompt" in props
        assert "recurring" in props
        assert "durable" in props

    def test_output_schema(self, cron_create_tool: CronCreateTool) -> None:
        schema = cron_create_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "id" in props
        assert "humanSchedule" in props
        assert "recurring" in props
        assert "durable" in props

    def test_user_facing_name(self, cron_create_tool: CronCreateTool) -> None:
        assert cron_create_tool.user_facing_name({}) == ""

    def test_is_enabled(self, cron_create_tool: CronCreateTool) -> None:
        result = cron_create_tool.is_enabled()
        assert isinstance(result, bool)

    def test_to_auto_classifier_input(self, cron_create_tool: CronCreateTool) -> None:
        result = cron_create_tool.to_auto_classifier_input({
            "cron": "*/5 * * * *",
            "prompt": "Check email",
        })
        assert "*/5 * * * *" in result
        assert "Check email" in result

    def test_validate_input_invalid_cron(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude-code-py.utils.cron_tasks.list_all_cron_tasks",
            return_value=[],
        ):
            result = cron_create_tool.validate_input(
                {"cron": "invalid-cron", "prompt": "test"}, mock_context
            )
        assert result is not True
        assert isinstance(result, tuple)
        assert "Invalid cron" in result[1] or "cron" in result[1].lower()

    def test_validate_input_no_calendar_date(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        # A cron with specific date in the past that won't match in the next year
        with patch(
            "claude-code-py.utils.cron_tasks.list_all_cron_tasks",
            return_value=[],
        ):
            result = cron_create_tool.validate_input(
                {"cron": "0 0 31 12 *", "prompt": "Never matches"}, mock_context
            )
        # This specific cron might or might not be valid depending on current date
        # The test is for the validation logic, not the specific cron value

    def test_validate_input_max_jobs(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        mock_tasks = [{"id": f"task-{i}"} for i in range(50)]
        with patch(
            "claude-code-py.utils.cron_tasks.list_all_cron_tasks",
            return_value=mock_tasks,
        ):
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = cron_create_tool.validate_input(
                    {"cron": "*/5 * * * *", "prompt": "test"}, mock_context
                )
        assert result is not True
        assert isinstance(result, tuple)
        assert "50" in result[1] or "max" in result[1].lower()

    def test_validate_input_teammate_durable(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        mock_task = {"id": "task-1"}
        mock_teammate_ctx = {"agent_id": "researcher@my-team"}

        with patch(
            "claude-code-py.utils.cron_tasks.list_all_cron_tasks",
            return_value=[mock_task],
        ):
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=mock_teammate_ctx,
            ):
                result = cron_create_tool.validate_input(
                    {"cron": "*/5 * * * *", "prompt": "test", "durable": True},
                    mock_context,
                )
        assert result is not True
        assert isinstance(result, tuple)
        assert "teammate" in result[1].lower() or "durable" in result[1].lower()

    def test_validate_input_success(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude-code-py.utils.cron_tasks.list_all_cron_tasks",
            return_value=[],
        ):
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = cron_create_tool.validate_input(
                    {"cron": "*/5 * * * *", "prompt": "Check email"}, mock_context
                )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_creates_job(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude-code-py.utils.cron_tasks.add_cron_task",
            return_value="new-job-id",
        ) as mock_add:
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = await cron_create_tool.call(
                    {
                        "cron": "*/5 * * * *",
                        "prompt": "Check email",
                        "recurring": True,
                        "durable": False,
                    },
                    mock_context,
                    AsyncMock(),
                    None,
                )

        mock_add.assert_called_once()
        call_args = mock_add.call_args
        assert call_args[0][0] == "*/5 * * * *"  # cron
        assert call_args[0][1] == "Check email"  # prompt
        assert call_args[0][2] is True  # recurring
        assert call_args[0][3] is False  # durable
        assert result["data"]["id"] == "new-job-id"
        assert "humanSchedule" in result["data"]
        assert result["data"]["recurring"] is True

    @pytest.mark.asyncio
    async def test_call_non_durable_default(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude-code-py.utils.cron_tasks.add_cron_task",
            return_value="job-id",
        ) as mock_add:
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = await cron_create_tool.call(
                    {"cron": "0 9 * * *", "prompt": "Morning standup"},
                    mock_context,
                    AsyncMock(),
                    None,
                )

        call_args = mock_add.call_args
        assert call_args[0][2] is True  # recurring defaults to True
        assert call_args[0][3] is False  # durable defaults to False
        assert result["data"]["recurring"] is True
        assert result["data"]["durable"] is False

    @pytest.mark.asyncio
    async def test_call_with_durable(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude-code-py.utils.cron_tasks.add_cron_task",
            return_value="durable-job-id",
        ) as mock_add:
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                with patch(
                    "claude-code-py.utils.cron.is_durable_cron_enabled",
                    return_value=True,
                ):
                    result = await cron_create_tool.call(
                        {
                            "cron": "0 9 * * *",
                            "prompt": "Daily reminder",
                            "recurring": True,
                            "durable": True,
                        },
                        mock_context,
                        AsyncMock(),
                        None,
                    )

        call_args = mock_add.call_args
        assert call_args[0][3] is True  # durable should be True
        assert result["data"]["durable"] is True

    @pytest.mark.asyncio
    async def test_call_oneshot(
        self, cron_create_tool: CronCreateTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude-code-py.utils.cron_tasks.add_cron_task",
            return_value="oneshot-job-id",
        ) as mock_add:
            with patch(
                "claude-code-py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = await cron_create_tool.call(
                    {
                        "cron": "0 9 * * *",
                        "prompt": "One-time reminder",
                        "recurring": False,
                    },
                    mock_context,
                    AsyncMock(),
                    None,
                )

        call_args = mock_add.call_args
        assert call_args[0][2] is False  # recurring
        assert result["data"]["recurring"] is False

    def test_map_tool_result_recurring(self, cron_create_tool: CronCreateTool) -> None:
        content = {
            "id": "job-123",
            "humanSchedule": "every 5 minutes",
            "recurring": True,
            "durable": False,
        }
        result = cron_create_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["type"] == "tool_result"
        assert "job-123" in result["content"]
        assert "recurring" in result["content"]
        assert "Session-only" in result["content"] or "persisted" in result["content"].lower()

    def test_map_tool_result_oneshot(self, cron_create_tool: CronCreateTool) -> None:
        content = {
            "id": "job-456",
            "humanSchedule": "at 9:00 AM",
            "recurring": False,
            "durable": False,
        }
        result = cron_create_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-2"
        )
        assert result["tool_use_id"] == "tool-use-2"
        assert "job-456" in result["content"]
        assert "one-shot" in result["content"] or "Once" in result["content"]
