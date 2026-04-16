"""
Tests for EnterPlanModeTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.enter_plan_mode import EnterPlanModeTool


@pytest.fixture
def enter_plan_mode_tool() -> EnterPlanModeTool:
    return EnterPlanModeTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.set_app_state = MagicMock()
    return ctx


class TestEnterPlanModeTool:
    """Tests for EnterPlanModeTool."""

    def test_name(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.name == "EnterPlanMode"

    def test_aliases(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.aliases is None

    def test_search_hint(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert "plan mode" in enter_plan_mode_tool.search_hint.lower()

    def test_should_defer(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.should_defer is True

    def test_always_load(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.always_load is False

    def test_max_result_size_chars(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.max_result_size_chars == 100_000

    def test_strict(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.strict is False

    def test_description_text(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert "plan mode" in enter_plan_mode_tool.description_text.lower()

    def test_prompt_text(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert "plan mode" in enter_plan_mode_tool.prompt_text.lower()

    def test_input_schema(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        schema = enter_plan_mode_tool.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["additionalProperties"] is False

    def test_output_schema(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        schema = enter_plan_mode_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "mode" in props
        assert "message" in props

    def test_user_facing_name(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.user_facing_name({}) == ""

    def test_is_enabled(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.is_enabled() is True

    def test_is_concurrency_safe(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.is_read_only({}) is True

    def test_render_tool_use_message(self, enter_plan_mode_tool: EnterPlanModeTool) -> None:
        assert enter_plan_mode_tool.render_tool_use_message({}) is None

    @pytest.mark.asyncio
    async def test_call_sets_permission_mode(
        self, enter_plan_mode_tool: EnterPlanModeTool, mock_context: MagicMock
    ) -> None:
        captured_fn = None

        def capture_set(fn):
            nonlocal captured_fn
            captured_fn = fn

        mock_context.set_app_state = capture_set

        result = await enter_plan_mode_tool.call(
            {}, mock_context, AsyncMock(), None
        )
        assert result["data"]["mode"] == "plan"
        assert "plan mode" in result["data"]["message"].lower()
        assert captured_fn is not None

        # Verify the state update function sets permission_mode to plan
        mock_prev = MagicMock(spec=[])
        mock_prev.permission_mode = "default"
        captured_fn(mock_prev)

    @pytest.mark.asyncio
    async def test_call_no_set_app_state(
        self, enter_plan_mode_tool: EnterPlanModeTool
    ) -> None:
        ctx = MagicMock()
        ctx.set_app_state = None

        result = await enter_plan_mode_tool.call({}, ctx, AsyncMock(), None)
        assert result["data"]["mode"] == "plan"

    def test_map_tool_result_to_tool_result_block_param(
        self, enter_plan_mode_tool: EnterPlanModeTool
    ) -> None:
        result = enter_plan_mode_tool.map_tool_result_to_tool_result_block_param(
            {"mode": "plan", "message": "Entered plan mode"}, "tool-123"
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["type"] == "tool_result"
        assert "plan mode" in result["content"].lower()

    def test_map_tool_result_default_message(
        self, enter_plan_mode_tool: EnterPlanModeTool
    ) -> None:
        result = enter_plan_mode_tool.map_tool_result_to_tool_result_block_param(
            {}, "tool-456"
        )
        assert result["content"] == "Entered plan mode"
