"""
Tests for AgentTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.agent import AgentTool, BUILTIN_AGENT_TYPES


@pytest.fixture
def agent_tool() -> AgentTool:
    return AgentTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.set_app_state = MagicMock()
    return ctx


class TestAgentTool:
    """Tests for AgentTool."""

    def test_name(self, agent_tool: AgentTool) -> None:
        assert agent_tool.name == "Agent"

    def test_aliases(self, agent_tool: AgentTool) -> None:
        assert agent_tool.aliases == ["Subagent"]

    def test_search_hint(self, agent_tool: AgentTool) -> None:
        assert "sub-agent" in agent_tool.search_hint.lower()

    def test_should_defer(self, agent_tool: AgentTool) -> None:
        assert agent_tool.should_defer is True

    def test_always_load(self, agent_tool: AgentTool) -> None:
        assert agent_tool.always_load is False

    def test_max_result_size_chars(self, agent_tool: AgentTool) -> None:
        assert agent_tool.max_result_size_chars == 100_000

    def test_strict(self, agent_tool: AgentTool) -> None:
        assert agent_tool.strict is False

    def test_description_text(self, agent_tool: AgentTool) -> None:
        assert "sub-agent" in agent_tool.description_text.lower()

    def test_prompt_text(self, agent_tool: AgentTool) -> None:
        assert "sub-agent" in agent_tool.prompt_text.lower()

    def test_input_schema(self, agent_tool: AgentTool) -> None:
        schema = agent_tool.input_schema
        assert schema["type"] == "object"
        assert "description" in schema["required"]
        assert "prompt" in schema["required"]
        props = schema["properties"]
        assert "description" in props
        assert "prompt" in props
        assert "subagent_type" in props
        assert "model" in props
        assert "run_in_background" in props
        assert "name" in props

    def test_output_schema(self, agent_tool: AgentTool) -> None:
        schema = agent_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "status" in props
        assert "agentId" in props
        assert "result" in props
        assert "error" in props

    def test_user_facing_name(self, agent_tool: AgentTool) -> None:
        assert agent_tool.user_facing_name({}) == "Agent"

    def test_is_enabled(self, agent_tool: AgentTool) -> None:
        assert agent_tool.is_enabled() is True

    def test_is_concurrency_safe(self, agent_tool: AgentTool) -> None:
        assert agent_tool.is_concurrency_safe({}) is True

    def test_render_tool_use_message(self, agent_tool: AgentTool) -> None:
        result = agent_tool.render_tool_use_message(
            {"description": "Fix the bug"}
        )
        assert result == "Running agent: Fix the bug"

    def test_render_tool_use_message_empty(self, agent_tool: AgentTool) -> None:
        result = agent_tool.render_tool_use_message({})
        assert result == "Running agent: "

    def test_to_auto_classifier_input(self, agent_tool: AgentTool) -> None:
        result = agent_tool.to_auto_classifier_input(
            {"subagent_type": "explore", "description": "find files"}
        )
        assert "explore" in result
        assert "find files" in result

    def test_to_auto_classifier_input_empty(self, agent_tool: AgentTool) -> None:
        result = agent_tool.to_auto_classifier_input({})
        assert "general-purpose" in result

    @pytest.mark.asyncio
    async def test_call_no_app_state(self, agent_tool: AgentTool) -> None:
        ctx = MagicMock()
        ctx.get_app_state = None
        ctx.set_app_state = None
        result = await agent_tool.call(
            {"description": "Test", "prompt": "Do something"},
            ctx,
            AsyncMock(),
            None,
        )
        assert result["data"]["status"] == "completed"
        assert "not available" in result["data"]["result"]

    @pytest.mark.asyncio
    async def test_call_sync_execution(
        self, agent_tool: AgentTool, mock_context: MagicMock
    ) -> None:
        result = await agent_tool.call(
            {"description": "Test", "prompt": "Do something"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["status"] == "completed"
        assert result["data"]["description"] == "Test"
        assert result["data"]["prompt"] == "Do something"

    @pytest.mark.asyncio
    async def test_call_background_launch(
        self, agent_tool: AgentTool, mock_context: MagicMock
    ) -> None:
        result = await agent_tool.call(
            {
                "description": "Background task",
                "prompt": "Do something in background",
                "run_in_background": True,
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["status"] == "async_launched"
        assert result["data"]["description"] == "Background task"
        assert result["data"]["agentId"] is not None

    @pytest.mark.asyncio
    async def test_call_background_with_name(
        self, agent_tool: AgentTool, mock_context: MagicMock
    ) -> None:
        result = await agent_tool.call(
            {
                "description": "Named agent",
                "prompt": "Test",
                "run_in_background": True,
                "name": "tester",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["status"] == "async_launched"
        assert result["data"]["agentId"] == "agent-tester"

    @pytest.mark.asyncio
    async def test_call_with_subagent_type(
        self, agent_tool: AgentTool, mock_context: MagicMock
    ) -> None:
        result = await agent_tool.call(
            {
                "description": "Explore codebase",
                "prompt": "Find all Python files",
                "subagent_type": "explore",
                "model": "sonnet",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["status"] == "completed"

    def test_map_tool_result_error(self, agent_tool: AgentTool) -> None:
        result = agent_tool.map_tool_result_to_tool_result_block_param(
            {"status": "completed", "error": "Agent failed"}, "tool-1"
        )
        assert result["tool_use_id"] == "tool-1"
        assert "error" in result["content"].lower()
        assert result.get("is_error") is True

    def test_map_tool_result_async_launched(self, agent_tool: AgentTool) -> None:
        result = agent_tool.map_tool_result_to_tool_result_block_param(
            {"status": "async_launched", "agentId": "agent-123"}, "tool-2"
        )
        assert result["tool_use_id"] == "tool-2"
        assert "agent-123" in result["content"]

    def test_map_tool_result_completed(self, agent_tool: AgentTool) -> None:
        result = agent_tool.map_tool_result_to_tool_result_block_param(
            {"status": "completed", "result": "Done!"}, "tool-3"
        )
        assert result["content"] == "Done!"

    def test_map_tool_result_empty(self, agent_tool: AgentTool) -> None:
        result = agent_tool.map_tool_result_to_tool_result_block_param(
            {"status": "completed"}, "tool-4"
        )
        assert result["content"] == "Agent completed"


class TestBuiltinAgentTypes:
    """Tests for BUILTIN_AGENT_TYPES."""

    def test_builtin_types_exist(self) -> None:
        assert "general-purpose" in BUILTIN_AGENT_TYPES
        assert "explore" in BUILTIN_AGENT_TYPES
        assert "plan" in BUILTIN_AGENT_TYPES
        assert "code-review" in BUILTIN_AGENT_TYPES

    def test_general_purpose_agent(self) -> None:
        agent = BUILTIN_AGENT_TYPES["general-purpose"]
        assert agent["name"] == "general-purpose"
        assert agent["model"] == "sonnet"

    def test_explore_agent(self) -> None:
        agent = BUILTIN_AGENT_TYPES["explore"]
        assert agent["name"] == "explore"
        assert agent["model"] == "sonnet"

    def test_plan_agent(self) -> None:
        agent = BUILTIN_AGENT_TYPES["plan"]
        assert agent["name"] == "plan"
        assert agent["model"] == "opus"

    def test_code_review_agent(self) -> None:
        agent = BUILTIN_AGENT_TYPES["code-review"]
        assert agent["name"] == "code-review"
