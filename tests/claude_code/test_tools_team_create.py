"""
Tests for TeamCreateTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.team_create import TeamCreateTool


@pytest.fixture
def team_create_tool() -> TeamCreateTool:
    return TeamCreateTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestTeamCreateTool:
    """Tests for TeamCreateTool."""

    def test_name(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.name == "TeamCreate"

    def test_aliases(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.aliases is None

    def test_search_hint(self, team_create_tool: TeamCreateTool) -> None:
        assert "swarm" in team_create_tool.search_hint.lower()

    def test_should_defer(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.should_defer is True

    def test_always_load(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.always_load is False

    def test_max_result_size_chars(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.max_result_size_chars == 100_000

    def test_strict(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.strict is False

    def test_description_text(self, team_create_tool: TeamCreateTool) -> None:
        assert "team" in team_create_tool.description_text.lower()

    def test_prompt_text(self, team_create_tool: TeamCreateTool) -> None:
        assert "team" in team_create_tool.prompt_text.lower()

    def test_input_schema(self, team_create_tool: TeamCreateTool) -> None:
        schema = team_create_tool.input_schema
        assert schema["type"] == "object"
        assert "team_name" in schema["required"]
        props = schema["properties"]
        assert "team_name" in props
        assert "description" in props
        assert "agent_type" in props

    def test_output_schema(self, team_create_tool: TeamCreateTool) -> None:
        schema = team_create_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "team_name" in props
        assert "team_file_path" in props
        assert "lead_agent_id" in props

    def test_user_facing_name(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.user_facing_name({}) == ""

    def test_is_enabled(self, team_create_tool: TeamCreateTool) -> None:
        assert team_create_tool.is_enabled() is True

    def test_to_auto_classifier_input(self, team_create_tool: TeamCreateTool) -> None:
        result = team_create_tool.to_auto_classifier_input({"team_name": "my-team"})
        assert result == "my-team"

    def test_to_auto_classifier_input_empty(self, team_create_tool: TeamCreateTool) -> None:
        result = team_create_tool.to_auto_classifier_input({})
        assert result == ""

    def test_validate_input_missing_team_name(
        self, team_create_tool: TeamCreateTool
    ) -> None:
        result = team_create_tool.validate_input({}, MagicMock())
        assert result is not True
        assert isinstance(result, tuple)
        assert result[1] == "team_name is required for TeamCreate"
        assert result[2] == 9

    def test_validate_input_empty_team_name(
        self, team_create_tool: TeamCreateTool
    ) -> None:
        result = team_create_tool.validate_input({"team_name": "   "}, MagicMock())
        assert result is not True
        assert isinstance(result, tuple)

    def test_validate_input_valid(self, team_create_tool: TeamCreateTool) -> None:
        result = team_create_tool.validate_input({"team_name": "my-team"}, MagicMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, team_create_tool: TeamCreateTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        ctx.set_app_state = None
        result = await team_create_tool.call(
            {"team_name": "test-team"}, ctx, AsyncMock(), None
        )
        assert result["data"]["success"] is False
        assert "Cannot access app state" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_creates_team(
        self, team_create_tool: TeamCreateTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.team_context = None
        result = await team_create_tool.call(
            {"team_name": "my-team", "description": "My team"}, mock_context, AsyncMock(), None
        )
        assert result["data"]["team_name"] == "my-team"
        assert "my-team" in result["data"]["team_file_path"]
        assert result["data"]["lead_agent_id"] == "team-lead@my-team"

    @pytest.mark.asyncio
    async def test_call_already_in_team(
        self, team_create_tool: TeamCreateTool, mock_context: MagicMock
    ) -> None:
        existing_team = MagicMock()
        existing_team.team_name = "existing-team"
        mock_context.get_app_state.return_value.team_context = existing_team

        result = await team_create_tool.call(
            {"team_name": "new-team"}, mock_context, AsyncMock(), None
        )
        assert result["data"]["success"] is False
        assert "existing-team" in result["data"]["message"]

    @pytest.mark.asyncio
    async def test_call_with_agent_type(
        self, team_create_tool: TeamCreateTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.team_context = None
        result = await team_create_tool.call(
            {"team_name": "research-team", "agent_type": "researcher"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["team_name"] == "research-team"

    @pytest.mark.asyncio
    async def test_call_default_agent_type(
        self, team_create_tool: TeamCreateTool, mock_context: MagicMock
    ) -> None:
        mock_context.get_app_state.return_value.team_context = None
        result = await team_create_tool.call(
            {"team_name": "default-team"}, mock_context, AsyncMock(), None
        )
        assert result["data"]["lead_agent_id"] == "team-lead@default-team"

    def test_map_tool_result_to_tool_result_block_param(
        self, team_create_tool: TeamCreateTool
    ) -> None:
        result = team_create_tool.map_tool_result_to_tool_result_block_param(
            {"team_name": "my-team", "lead_agent_id": "team-lead@my-team"},
            "tool-123",
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["type"] == "tool_result"
        assert result["content"][0]["type"] == "text"
        assert "my-team" in result["content"][0]["text"]
