"""
Tests for TeamDeleteTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.team_delete import TeamDeleteTool


@pytest.fixture
def team_delete_tool() -> TeamDeleteTool:
    return TeamDeleteTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestTeamDeleteTool:
    """Tests for TeamDeleteTool."""

    def test_name(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.name == "TeamDelete"

    def test_aliases(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.aliases is None

    def test_search_hint(self, team_delete_tool: TeamDeleteTool) -> None:
        assert "swarm" in team_delete_tool.search_hint.lower()

    def test_should_defer(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.should_defer is True

    def test_always_load(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.always_load is False

    def test_max_result_size_chars(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.max_result_size_chars == 100_000

    def test_strict(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.strict is False

    def test_description_text(self, team_delete_tool: TeamDeleteTool) -> None:
        assert "clean" in team_delete_tool.description_text.lower()

    def test_prompt_text(self, team_delete_tool: TeamDeleteTool) -> None:
        assert "team" in team_delete_tool.prompt_text.lower()

    def test_input_schema(self, team_delete_tool: TeamDeleteTool) -> None:
        schema = team_delete_tool.input_schema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema["additionalProperties"] is False

    def test_output_schema(self, team_delete_tool: TeamDeleteTool) -> None:
        schema = team_delete_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "success" in props
        assert "message" in props
        assert "team_name" in props

    def test_user_facing_name(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.user_facing_name({}) == ""

    def test_is_enabled(self, team_delete_tool: TeamDeleteTool) -> None:
        assert team_delete_tool.is_enabled() is True

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, team_delete_tool: TeamDeleteTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        ctx.set_app_state = None
        result = await team_delete_tool.call({}, ctx, AsyncMock(), None)
        assert result["data"]["success"] is False
        assert "Cannot access app state" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_no_team(
        self, team_delete_tool: TeamDeleteTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.team_context = None
        result = await team_delete_tool.call({}, mock_context, AsyncMock(), None)
        assert result["data"]["success"] is True
        assert "nothing to clean up" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_no_team_name(
        self, team_delete_tool: TeamDeleteTool, mock_context: MagicMock
    ) -> None:
        team_ctx = MagicMock()
        team_ctx.team_name = None
        mock_context.get_app_state.return_value.team_context = team_ctx
        result = await team_delete_tool.call({}, mock_context, AsyncMock(), None)
        assert result["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_call_active_members_prevent_cleanup(
        self, team_delete_tool: TeamDeleteTool, mock_context: MagicMock
    ) -> None:
        team_ctx = MagicMock()
        team_ctx.team_name = "active-team"
        team_ctx.teammates = {
            "dev-1": MagicMock(is_active=True),
            "dev-2": MagicMock(is_active=True),
        }
        mock_context.get_app_state.return_value.team_context = team_ctx

        result = await team_delete_tool.call({}, mock_context, AsyncMock(), None)
        assert result["data"]["success"] is False
        assert "active member" in result["data"]["message"]
        assert "dev-1" in result["data"]["message"]
        assert "dev-2" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_inactive_members_ok(
        self, team_delete_tool: TeamDeleteTool, mock_context: MagicMock
    ) -> None:
        team_ctx = MagicMock()
        team_ctx.team_name = "clean-team"
        team_ctx.teammates = {
            "dev-1": MagicMock(is_active=False),
            "team-lead": MagicMock(is_active=True),
        }
        mock_context.get_app_state.return_value.team_context = team_ctx

        result = await team_delete_tool.call({}, mock_context, AsyncMock(), None)
        assert result["data"]["success"] is True
        assert "clean-team" in result["data"]["team_name"]

    @pytest.mark.asyncio
    async def test_call_clears_team_context(
        self, team_delete_tool: TeamDeleteTool, mock_context: MagicMock
    ) -> None:
        team_ctx = MagicMock()
        team_ctx.team_name = "cleanup-team"
        team_ctx.teammates = {}
        mock_context.get_app_state.return_value.team_context = team_ctx

        captured_fn = None

        def capture_set(fn):
            nonlocal captured_fn
            captured_fn = fn

        mock_context.set_app_state = capture_set

        result = await team_delete_tool.call({}, mock_context, AsyncMock(), None)
        assert result["data"]["success"] is True
        assert captured_fn is not None

    def test_map_tool_result_to_tool_result_block_param(
        self, team_delete_tool: TeamDeleteTool
    ) -> None:
        result = team_delete_tool.map_tool_result_to_tool_result_block_param(
            {"success": True, "team_name": "my-team", "message": "Cleaned up"},
            "tool-123",
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["type"] == "tool_result"
        assert result["content"][0]["type"] == "text"
        assert "my-team" in result["content"][0]["text"]
