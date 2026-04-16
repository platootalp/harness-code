"""
Tests for ExitPlanModeTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.exit_plan_mode import ExitPlanModeTool


@pytest.fixture
def exit_plan_mode_tool() -> ExitPlanModeTool:
    return ExitPlanModeTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.set_app_state = MagicMock()
    return ctx


class TestExitPlanModeTool:
    """Tests for ExitPlanModeTool."""

    def test_name(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.name == "ExitPlanMode"

    def test_aliases(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.aliases == ["ExitPlanModeV2"]

    def test_search_hint(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert "plan mode" in exit_plan_mode_tool.search_hint.lower()

    def test_should_defer(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.should_defer is True

    def test_always_load(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.always_load is False

    def test_max_result_size_chars(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.max_result_size_chars == 100_000

    def test_strict(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.strict is False

    def test_description_text(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert "plan mode" in exit_plan_mode_tool.description_text.lower()

    def test_prompt_text(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert "plan mode" in exit_plan_mode_tool.prompt_text.lower()

    def test_input_schema(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        schema = exit_plan_mode_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "allowedPrompts" in props
        assert schema["additionalProperties"] is False

    def test_output_schema(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        schema = exit_plan_mode_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "approved" in props
        assert "mode" in props
        assert "message" in props

    def test_user_facing_name(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.user_facing_name({}) == ""

    def test_is_enabled(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.is_enabled() is True

    def test_is_concurrency_safe(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.is_concurrency_safe({}) is True

    def test_render_tool_use_message(self, exit_plan_mode_tool: ExitPlanModeTool) -> None:
        assert exit_plan_mode_tool.render_tool_use_message({}) is None

    @pytest.mark.asyncio
    async def test_call_sets_permission_mode(
        self, exit_plan_mode_tool: ExitPlanModeTool, mock_context: MagicMock
    ) -> None:
        captured_fn = None

        def capture_set(fn):
            nonlocal captured_fn
            captured_fn = fn

        mock_context.set_app_state = capture_set

        result = await exit_plan_mode_tool.call(
            {}, mock_context, AsyncMock(), None
        )
        assert result["data"]["approved"] is True
        assert result["data"]["mode"] == "default"
        assert "approved" in result["data"]["message"].lower()
        assert captured_fn is not None

    @pytest.mark.asyncio
    async def test_call_no_set_app_state(
        self, exit_plan_mode_tool: ExitPlanModeTool
    ) -> None:
        ctx = MagicMock()
        ctx.set_app_state = None

        result = await exit_plan_mode_tool.call({}, ctx, AsyncMock(), None)
        assert result["data"]["approved"] is True
        assert result["data"]["mode"] == "default"

    @pytest.mark.asyncio
    async def test_call_with_allowed_prompts(
        self, exit_plan_mode_tool: ExitPlanModeTool, mock_context: MagicMock
    ) -> None:
        captured_fn = None

        def capture_set(fn):
            nonlocal captured_fn
            captured_fn = fn

        mock_context.set_app_state = capture_set

        result = await exit_plan_mode_tool.call(
            {
                "allowedPrompts": [
                    {"tool": "Bash", "prompt": "run tests"},
                    {"tool": "Write", "prompt": "edit files"},
                ]
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["approved"] is True

    def test_map_tool_result_to_tool_result_block_param(
        self, exit_plan_mode_tool: ExitPlanModeTool
    ) -> None:
        result = exit_plan_mode_tool.map_tool_result_to_tool_result_block_param(
            {
                "approved": True,
                "mode": "default",
                "message": "Plan approved",
            },
            "tool-123",
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["type"] == "tool_result"
        assert result["content"] == "Plan approved"

    def test_map_tool_result_default_content(
        self, exit_plan_mode_tool: ExitPlanModeTool
    ) -> None:
        result = exit_plan_mode_tool.map_tool_result_to_tool_result_block_param(
            {}, "tool-456"
        )
        assert result["content"] == "Exited plan mode"
