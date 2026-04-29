"""
Tests for WebFetchTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_code.tools.web_fetch import WebFetchTool, WebFetchToolOutput


@pytest.fixture
def web_fetch_tool() -> WebFetchTool:
    return WebFetchTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


class TestWebFetchTool:
    """Tests for WebFetchTool."""

    def test_name(self, web_fetch_tool: WebFetchTool) -> None:
        assert web_fetch_tool.name == "WebFetch"

    def test_input_schema(self, web_fetch_tool: WebFetchTool) -> None:
        schema = web_fetch_tool.input_schema
        assert schema["type"] == "object"
        assert "url" in schema["required"]
        assert "prompt" in schema["required"]
        assert "url" in schema["properties"]
        assert "prompt" in schema["properties"]

    def test_is_concurrency_safe(self, web_fetch_tool: WebFetchTool) -> None:
        assert web_fetch_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, web_fetch_tool: WebFetchTool) -> None:
        assert web_fetch_tool.is_read_only({}) is True

    def test_is_open_world(self, web_fetch_tool: WebFetchTool) -> None:
        assert web_fetch_tool.is_open_world({}) is True

    def test_is_search_command(self, web_fetch_tool: WebFetchTool) -> None:
        result = web_fetch_tool.is_search_or_read_command({})
        assert result["is_search"] is False
        assert result["is_read"] is True

    def test_to_auto_classifier_input(self, web_fetch_tool: WebFetchTool) -> None:
        result = web_fetch_tool.to_auto_classifier_input(
            {"url": "https://example.com/path"}
        )
        assert result == "example.com"

    def test_max_result_size_chars(self, web_fetch_tool: WebFetchTool) -> None:
        assert web_fetch_tool.max_result_size_chars == 100_000

    def test_should_defer(self, web_fetch_tool: WebFetchTool) -> None:
        assert web_fetch_tool.should_defer is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_url(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_missing_prompt(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.validate_input(
            {"url": "https://example.com"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_invalid_url(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.validate_input(
            {"url": "not-a-url", "prompt": "test"}, mock_context
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_invalid_scheme(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.validate_input(
            {"url": "ftp://example.com", "prompt": "test"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_missing_host(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.validate_input(
            {"url": "http://", "prompt": "test"}, mock_context
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_valid(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.validate_input(
            {"url": "https://example.com", "prompt": "test"}, mock_context
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_http_error(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.call(
            {"url": "https://invalid-domain-xyz123.none", "prompt": "test"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, WebFetchToolOutput)
        assert result.data.code != 200
        assert result.data.url == "https://invalid-domain-xyz123.none"

    @pytest.mark.asyncio
    async def test_call_duration_reported(
        self, web_fetch_tool: WebFetchTool, mock_context: MagicMock
    ) -> None:
        result = await web_fetch_tool.call(
            {"url": "https://invalid-domain-xyz.none", "prompt": "test"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_description(self, web_fetch_tool: WebFetchTool) -> None:
        desc = await web_fetch_tool.description(
            {"url": "https://example.com", "prompt": "test"}, {}
        )
        assert "example.com" in desc or "fetch" in desc.lower()

    @pytest.mark.asyncio
    async def test_prompt(self, web_fetch_tool: WebFetchTool) -> None:
        prompt = await web_fetch_tool.prompt({})
        assert "WebFetch" in prompt or "fetch" in prompt.lower()


class TestWebFetchToolOutput:
    """Tests for WebFetchToolOutput dataclass."""

    def test_output_creation(self) -> None:
        output = WebFetchToolOutput(
            bytes=100,
            code=200,
            code_text="OK",
            result="content",
            duration_ms=50.0,
            url="https://example.com",
        )
        assert output.bytes == 100
        assert output.code == 200
        assert output.code_text == "OK"
        assert output.result == "content"
        assert output.duration_ms == 50.0
        assert output.url == "https://example.com"


class TestApplyPrompt:
    """Tests for the _apply_prompt helper."""

    @pytest.mark.asyncio
    async def test_apply_prompt_summary(self, web_fetch_tool: WebFetchTool) -> None:
        content = "a" * 600
        result = web_fetch_tool._apply_prompt(content, "summarize this")
        assert len(result) <= 600
        assert "..." in result

    @pytest.mark.asyncio
    async def test_apply_prompt_extract(self, web_fetch_tool: WebFetchTool) -> None:
        content = "\n".join([f"line {i}" for i in range(100)])
        result = web_fetch_tool._apply_prompt(content, "extract the data")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_apply_prompt_default(self, web_fetch_tool: WebFetchTool) -> None:
        content = "hello world"
        result = web_fetch_tool._apply_prompt(content, "get content")
        assert result == content
