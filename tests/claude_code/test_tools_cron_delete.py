"""
Tests for CronDeleteTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_code.tools.cron_delete import CronDeleteTool


@pytest.fixture
def cron_delete_tool() -> CronDeleteTool:
    return CronDeleteTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestCronDeleteTool:
    """Tests for CronDeleteTool."""

    def test_name(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.name == "CronDelete"

    def test_aliases(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.aliases is None

    def test_search_hint(self, cron_delete_tool: CronDeleteTool) -> None:
        assert "cancel" in cron_delete_tool.search_hint.lower()
        assert "cron" in cron_delete_tool.search_hint.lower()

    def test_should_defer(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.should_defer is True

    def test_always_load(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.always_load is False

    def test_max_result_size_chars(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.max_result_size_chars == 100_000

    def test_strict(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.strict is False

    def test_description_text(self, cron_delete_tool: CronDeleteTool) -> None:
        assert "cancel" in cron_delete_tool.description_text.lower()
        assert "cron" in cron_delete_tool.description_text.lower()

    def test_prompt_text(self, cron_delete_tool: CronDeleteTool) -> None:
        assert "cancel" in cron_delete_tool.prompt_text.lower()

    def test_input_schema(self, cron_delete_tool: CronDeleteTool) -> None:
        schema = cron_delete_tool.input_schema
        assert schema["type"] == "object"
        assert "id" in schema["required"]
        assert "id" in schema["properties"]
        assert schema["properties"]["id"]["type"] == "string"

    def test_output_schema(self, cron_delete_tool: CronDeleteTool) -> None:
        schema = cron_delete_tool.output_schema
        assert schema["type"] == "object"
        assert "id" in schema["properties"]

    def test_user_facing_name(self, cron_delete_tool: CronDeleteTool) -> None:
        assert cron_delete_tool.user_facing_name({}) == ""

    def test_is_enabled(self, cron_delete_tool: CronDeleteTool) -> None:
        result = cron_delete_tool.is_enabled()
        assert isinstance(result, bool)

    def test_to_auto_classifier_input(self, cron_delete_tool: CronDeleteTool) -> None:
        result = cron_delete_tool.to_auto_classifier_input({"id": "job-123"})
        assert result == "job-123"

    def test_validate_input_missing_id(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        result = cron_delete_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)

    def test_validate_input_job_not_found(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude_code.utils.cron_tasks.list_all_cron_tasks",
            return_value=[],
        ):
            result = cron_delete_tool.validate_input(
                {"id": "nonexistent-job"}, mock_context
            )
        assert result is not True
        assert isinstance(result, tuple)
        assert "nonexistent-job" in result[1]

    def test_validate_input_owned_by_other(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        mock_task = {"id": "job-123", "agent_id": "other-agent@my-team"}
        mock_teammate_ctx = {"agent_id": "researcher@my-team"}

        with patch(
            "claude_code.utils.cron_tasks.list_all_cron_tasks",
            return_value=[mock_task],
        ):
            with patch(
                "claude_code.utils.teammate_context.get_teammate_context",
                return_value=mock_teammate_ctx,
            ):
                result = cron_delete_tool.validate_input(
                    {"id": "job-123"}, mock_context
                )
        assert result is not True
        assert isinstance(result, tuple)
        assert "another agent" in result[1]

    def test_validate_input_success(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        mock_task = {"id": "job-123", "agent_id": "researcher@my-team"}
        mock_teammate_ctx = {"agent_id": "researcher@my-team"}

        with patch(
            "claude_code.utils.cron_tasks.list_all_cron_tasks",
            return_value=[mock_task],
        ):
            with patch(
                "claude_code.utils.teammate_context.get_teammate_context",
                return_value=mock_teammate_ctx,
            ):
                result = cron_delete_tool.validate_input(
                    {"id": "job-123"}, mock_context
                )
        assert result is True

    def test_validate_input_team_lead_sees_all(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        mock_task = {"id": "job-123", "agent_id": "researcher@my-team"}

        with patch(
            "claude_code.utils.cron_tasks.list_all_cron_tasks",
            return_value=[mock_task],
        ):
            with patch(
                "claude_code.utils.teammate_context.get_teammate_context",
                return_value=None,
            ):
                result = cron_delete_tool.validate_input(
                    {"id": "job-123"}, mock_context
                )
        # Team lead (no teammate context) can delete any job
        assert result is True

    @pytest.mark.asyncio
    async def test_call_deletes_job(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        with patch(
            "claude_code.utils.cron_tasks.remove_cron_tasks",
        ) as mock_remove:
            result = await cron_delete_tool.call(
                {"id": "job-123"},
                mock_context,
                AsyncMock(),
                None,
            )

        mock_remove.assert_called_once_with(["job-123"])
        assert result["data"]["id"] == "job-123"

    @pytest.mark.asyncio
    async def test_call_job_not_found_in_call(
        self, cron_delete_tool: CronDeleteTool, mock_context: MagicMock
    ) -> None:
        # Even if the job is not found during call(), it should still succeed
        # (idempotent deletion)
        with patch(
            "claude_code.utils.cron_tasks.remove_cron_tasks",
        ) as mock_remove:
            result = await cron_delete_tool.call(
                {"id": "nonexistent"},
                mock_context,
                AsyncMock(),
                None,
            )

        mock_remove.assert_called_once()
        assert result["data"]["id"] == "nonexistent"

    def test_map_tool_result_to_tool_result_block_param(
        self, cron_delete_tool: CronDeleteTool
    ) -> None:
        result = cron_delete_tool.map_tool_result_to_tool_result_block_param(
            {"id": "job-456"}, "tool-use-1"
        )
        assert result["tool_use_id"] == "tool-use-1"
        assert result["type"] == "tool_result"
        assert "job-456" in result["content"]
        assert "Cancelled" in result["content"] or "cancelled" in result["content"].lower()
