"""
Tests for WebSearchTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.web_search import (
    SearchHit,
    SearchResult,
    WebSearchTool,
    WebSearchToolOutput,
)


@pytest.fixture
def web_search_tool() -> WebSearchTool:
    return WebSearchTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    def test_name(self, web_search_tool: WebSearchTool) -> None:
        assert web_search_tool.name == "WebSearch"

    def test_input_schema(self, web_search_tool: WebSearchTool) -> None:
        schema = web_search_tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["required"]
        assert "query" in schema["properties"]
        assert "allowed_domains" in schema["properties"]
        assert "blocked_domains" in schema["properties"]

    def test_is_concurrency_safe(self, web_search_tool: WebSearchTool) -> None:
        assert web_search_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, web_search_tool: WebSearchTool) -> None:
        assert web_search_tool.is_read_only({}) is False

    def test_is_open_world(self, web_search_tool: WebSearchTool) -> None:
        assert web_search_tool.is_open_world({}) is True

    def test_is_search_command(self, web_search_tool: WebSearchTool) -> None:
        result = web_search_tool.is_search_or_read_command({})
        assert result["is_search"] is True
        assert result["is_read"] is False

    def test_to_auto_classifier_input(self, web_search_tool: WebSearchTool) -> None:
        result = web_search_tool.to_auto_classifier_input({"query": "python tutorial"})
        assert result == "python tutorial"

    def test_should_defer(self, web_search_tool: WebSearchTool) -> None:
        assert web_search_tool.should_defer is True

    def test_max_result_size_chars(self, web_search_tool: WebSearchTool) -> None:
        assert web_search_tool.max_result_size_chars == 100_000

    @pytest.mark.asyncio
    async def test_validate_input_missing_query(
        self, web_search_tool: WebSearchTool, mock_context: MagicMock
    ) -> None:
        result = await web_search_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_too_short(
        self, web_search_tool: WebSearchTool, mock_context: MagicMock
    ) -> None:
        result = await web_search_tool.validate_input(
            {"query": "a"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_valid(
        self, web_search_tool: WebSearchTool, mock_context: MagicMock
    ) -> None:
        result = await web_search_tool.validate_input(
            {"query": "python tutorial"}, mock_context
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_basic(
        self, web_search_tool: WebSearchTool, mock_context: MagicMock
    ) -> None:
        result = await web_search_tool.call(
            {"query": "test query"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, WebSearchToolOutput)
        assert result.data.query == "test query"
        assert isinstance(result.data.results, list)
        assert result.data.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_call_with_domain_filters(
        self, web_search_tool: WebSearchTool, mock_context: MagicMock
    ) -> None:
        result = await web_search_tool.call(
            {
                "query": "test",
                "allowed_domains": ["example.com"],
                "blocked_domains": ["banned.com"],
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.query == "test"

    @pytest.mark.asyncio
    async def test_description(self, web_search_tool: WebSearchTool) -> None:
        desc = await web_search_tool.description({"query": "python"}, {})
        assert "python" in desc or "search" in desc.lower()

    @pytest.mark.asyncio
    async def test_prompt(self, web_search_tool: WebSearchTool) -> None:
        prompt = await web_search_tool.prompt({})
        assert "WebSearch" in prompt
        assert "8" in prompt  # MAX_SEARCH_USES


class TestSearchHit:
    """Tests for SearchHit dataclass."""

    def test_search_hit_creation(self) -> None:
        hit = SearchHit(title="Test", url="https://example.com")
        assert hit.title == "Test"
        assert hit.url == "https://example.com"

    def test_search_hit_repr(self) -> None:
        hit = SearchHit(title="Test", url="https://example.com")
        assert "Test" in repr(hit)


class TestWebSearchToolOutput:
    """Tests for WebSearchToolOutput dataclass."""

    def test_output_creation(self) -> None:
        output = WebSearchToolOutput(
            query="test",
            results=[],
            duration_seconds=1.5,
        )
        assert output.query == "test"
        assert output.results == []
        assert output.duration_seconds == 1.5
