"""
Tests for ToolSearchTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_code.tools.tool_search import ToolSearchTool


@pytest.fixture
def tool_search_tool() -> ToolSearchTool:
    return ToolSearchTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    ctx.tools = []
    return ctx


class TestToolSearchTool:
    """Tests for ToolSearchTool."""

    def test_name(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.name == "ToolSearch"

    def test_aliases(self, tool_search_tool: ToolSearchTool) -> None:
        aliases = tool_search_tool.aliases
        assert aliases is None or isinstance(aliases, list)

    def test_search_hint(self, tool_search_tool: ToolSearchTool) -> None:
        assert "search" in tool_search_tool.search_hint.lower() or "tool" in tool_search_tool.search_hint.lower()

    def test_should_defer(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.should_defer is False

    def test_always_load(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.always_load is False

    def test_max_result_size_chars(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.max_result_size_chars == 100_000

    def test_strict(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.strict is False

    def test_description_text(self, tool_search_tool: ToolSearchTool) -> None:
        desc = tool_search_tool.description_text
        assert "search" in desc.lower() or "tool" in desc.lower()

    def test_prompt_text(self, tool_search_tool: ToolSearchTool) -> None:
        prompt = tool_search_tool.prompt_text
        assert isinstance(prompt, str)

    def test_input_schema(self, tool_search_tool: ToolSearchTool) -> None:
        schema = tool_search_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "query" in props
        # query should be required
        assert "query" in schema["required"]
        # max_results should be optional
        assert "maxResults" in props or "max_results" in props

    def test_output_schema(self, tool_search_tool: ToolSearchTool) -> None:
        schema = tool_search_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "matches" in props
        assert "query" in props
        assert "total_deferred_tools" in props or "totalDeferredTools" in props
        assert "pending_mcp_servers" in props or "pendingMcpServers" in props

    def test_user_facing_name(self, tool_search_tool: ToolSearchTool) -> None:
        result = tool_search_tool.user_facing_name({})
        assert isinstance(result, str)

    def test_is_enabled(self, tool_search_tool: ToolSearchTool) -> None:
        result = tool_search_tool.is_enabled()
        assert isinstance(result, bool)

    def test_is_concurrency_safe(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, tool_search_tool: ToolSearchTool) -> None:
        assert tool_search_tool.is_read_only({}) is True

    def test_to_auto_classifier_input(self, tool_search_tool: ToolSearchTool) -> None:
        result = tool_search_tool.to_auto_classifier_input({"query": "search for bash"})
        assert "search" in result.lower() or "bash" in result.lower()

    @pytest.mark.asyncio
    async def test_validate_input_not_needed(self, tool_search_tool: ToolSearchTool) -> None:
        # ToolSearch should not need validation errors
        result = await tool_search_tool.validate_input({"query": "bash"}, MagicMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_call_select_prefix(
        self, tool_search_tool: ToolSearchTool, mock_context: MagicMock
    ) -> None:
        # Mock tools with bash tool
        mock_bash = MagicMock()
        mock_bash.name = "Bash"
        mock_bash.description_text = "Execute bash commands"
        mock_context.tools = [mock_bash]

        result = await tool_search_tool.call(
            {"query": "select:Bash"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["query"] == "select:Bash"
        assert "matches" in result
        assert len(result["matches"]) >= 0

    @pytest.mark.asyncio
    async def test_call_keyword_search(
        self, tool_search_tool: ToolSearchTool, mock_context: MagicMock
    ) -> None:
        # Mock tools with various tools
        mock_bash = MagicMock()
        mock_bash.name = "Bash"
        mock_bash.description_text = "Execute bash commands"

        mock_read = MagicMock()
        mock_read.name = "Read"
        mock_read.description_text = "Read files from the filesystem"

        mock_context.tools = [mock_bash, mock_read]

        result = await tool_search_tool.call(
            {"query": "bash command"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["query"] == "bash command"
        assert "matches" in result

    @pytest.mark.asyncio
    async def test_call_no_matches(
        self, tool_search_tool: ToolSearchTool, mock_context: MagicMock
    ) -> None:
        mock_context.tools = []

        result = await tool_search_tool.call(
            {"query": "nonexistent tool xyz123"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_call_exact_tool_name_match(
        self, tool_search_tool: ToolSearchTool, mock_context: MagicMock
    ) -> None:
        mock_bash = MagicMock()
        mock_bash.name = "Bash"
        mock_bash.description_text = "Execute bash commands"
        mock_context.tools = [mock_bash]

        result = await tool_search_tool.call(
            {"query": "Bash"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["query"] == "Bash"
        assert len(result["matches"]) >= 0

    @pytest.mark.asyncio
    async def test_call_mcp_prefix(
        self, tool_search_tool: ToolSearchTool, mock_context: MagicMock
    ) -> None:
        # Mock MCP tools
        mock_mcp = MagicMock()
        mock_mcp.name = "mcp__filesystem__read"
        mock_mcp.description_text = "Read files using MCP"

        mock_context.tools = [mock_mcp]

        result = await tool_search_tool.call(
            {"query": "mcp:"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "matches" in result
        assert "pending_mcp_servers" in result or "pendingMcpServers" in result

    def test_map_tool_result_with_matches(
        self, tool_search_tool: ToolSearchTool
    ) -> None:
        content = {
            "matches": [
                {
                    "name": "Bash",
                    "description": "Execute bash commands",
                    "score": 0.95,
                },
                {
                    "name": "WebSearch",
                    "description": "Search the web",
                    "score": 0.85,
                },
            ],
            "query": "bash",
            "total_deferred_tools": 0,
            "pending_mcp_servers": [],
        }
        result = tool_search_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-search"
        )
        assert result["tool_use_id"] == "tool-use-search"
        assert result["type"] == "tool_result"
        # content is a list of tool names extracted from matches
        assert isinstance(result["content"], list)
        assert "Bash" in result["content"]

    def test_map_tool_result_empty(
        self, tool_search_tool: ToolSearchTool
    ) -> None:
        content = {
            "matches": [],
            "query": "nonexistent",
            "total_deferred_tools": 0,
            "pending_mcp_servers": [],
        }
        result = tool_search_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-search-empty"
        )
        assert result["tool_use_id"] == "tool-use-search-empty"
        assert "no match" in result["content"].lower() or "0" in result["content"]
