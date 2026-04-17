"""
Tests for CronListTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_code.tools.cron_list import CronListTool


@pytest.fixture
def cron_list_tool() -> CronListTool:
    return CronListTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestCronListTool:
    """Tests for CronListTool."""

    def test_name(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.name == "CronList"

    def test_aliases(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.aliases is None

    def test_search_hint(self, cron_list_tool: CronListTool) -> None:
        assert "cron" in cron_list_tool.search_hint.lower()
        assert "job" in cron_list_tool.search_hint.lower()

    def test_should_defer(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.should_defer is True

    def test_always_load(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.always_load is False

    def test_max_result_size_chars(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.max_result_size_chars == 100_000

    def test_strict(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.strict is False

    def test_description_text(self, cron_list_tool: CronListTool) -> None:
        assert "cron" in cron_list_tool.description_text.lower()

    def test_prompt_text(self, cron_list_tool: CronListTool) -> None:
        assert "cron" in cron_list_tool.prompt_text.lower()

    def test_input_schema(self, cron_list_tool: CronListTool) -> None:
        schema = cron_list_tool.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["additionalProperties"] is False

    def test_output_schema(self, cron_list_tool: CronListTool) -> None:
        schema = cron_list_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "jobs" in props
        assert schema["properties"]["jobs"]["type"] == "array"
        job_props = schema["properties"]["jobs"]["items"]["properties"]
        assert "id" in job_props
        assert "cron" in job_props
        assert "humanSchedule" in job_props
        assert "prompt" in job_props

    def test_user_facing_name(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.user_facing_name({}) == ""

    def test_is_enabled(self, cron_list_tool: CronListTool) -> None:
        # isEnabled checks isKairosCronEnabled - should be a boolean
        result = cron_list_tool.is_enabled()
        assert isinstance(result, bool)

    def test_is_concurrency_safe(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, cron_list_tool: CronListTool) -> None:
        assert cron_list_tool.is_read_only({}) is True

    def test_to_auto_classifier_input(self, cron_list_tool: CronListTool) -> None:
        result = cron_list_tool.to_auto_classifier_input({})
        # Empty input for read-only list tool
        assert result == ""

    @pytest.mark.asyncio
    async def test_call_returns_jobs(
        self, cron_list_tool: CronListTool, mock_context: MagicMock
    ) -> None:
        mock_task1 = {
            "id": "job-1",
            "cron": "*/5 * * * *",
            "prompt": "Check email",
            "recurring": True,
            "durable": True,
            "agent_id": "team-lead@my-team",
        }

        mock_task2 = {
            "id": "job-2",
            "cron": "0 9 * * *",
            "prompt": "Morning standup",
            "recurring": False,
            "durable": False,
            "agent_id": "team-lead@my-team",
        }

        with patch(
            "claw_py.utils.cron_tasks.list_all_cron_tasks",
            return_value=[mock_task1, mock_task2],
        ):
            with patch(
                "claw_py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = await cron_list_tool.call(
                    {},
                    mock_context,
                    AsyncMock(),
                    None,
                )

        assert "data" in result
        assert "jobs" in result["data"]
        assert len(result["data"]["jobs"]) == 2
        job1 = result["data"]["jobs"][0]
        assert job1["id"] == "job-1"
        assert job1["cron"] == "*/5 * * * *"
        assert "humanSchedule" in job1
        assert job1["prompt"] == "Check email"
        assert job1["recurring"] is True

    @pytest.mark.asyncio
    async def test_call_empty_jobs(
        self, cron_list_tool: CronListTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claw_py.utils.cron_tasks.list_all_cron_tasks",
            return_value=[],
        ):
            with patch(
                "claw_py.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = await cron_list_tool.call(
                    {},
                    mock_context,
                    AsyncMock(),
                    None,
                )

        assert result["data"]["jobs"] == []

    def test_map_tool_result_with_jobs(self, cron_list_tool: CronListTool) -> None:
        content = {
            "jobs": [
                {
                    "id": "job-1",
                    "cron": "*/5 * * * *",
                    "humanSchedule": "every 5 minutes",
                    "prompt": "Check email inbox",
                    "recurring": True,
                },
                {
                    "id": "job-2",
                    "cron": "0 9 * * *",
                    "humanSchedule": "at 9:00 AM",
                    "prompt": "Morning standup",
                    "recurring": False,
                    "durable": False,
                },
            ]
        }
        result = cron_list_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["type"] == "tool_result"
        assert "job-1" in result["content"]
        assert "every 5 minutes" in result["content"]
        assert "recurring" in result["content"]
        assert "job-2" in result["content"]
        assert "one-shot" in result["content"]

    def test_map_tool_result_empty(self, cron_list_tool: CronListTool) -> None:
        content = {"jobs": []}
        result = cron_list_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-2"
        )
        assert result["tool_use_id"] == "tool-use-2"
        assert result["type"] == "tool_result"
        assert "No scheduled jobs" in result["content"]
