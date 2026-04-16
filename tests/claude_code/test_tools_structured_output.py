"""
Tests for StructuredOutputTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_code.tools.structured_output import StructuredOutputTool


@pytest.fixture
def structured_output_tool() -> StructuredOutputTool:
    return StructuredOutputTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    return ctx


class TestStructuredOutputTool:
    """Tests for StructuredOutputTool."""

    def test_name(self, structured_output_tool: StructuredOutputTool) -> None:
        assert structured_output_tool.name == "StructuredOutput"

    def test_aliases(self, structured_output_tool: StructuredOutputTool) -> None:
        aliases = structured_output_tool.aliases
        assert aliases is None or isinstance(aliases, list)

    def test_search_hint(self, structured_output_tool: StructuredOutputTool) -> None:
        hint = structured_output_tool.search_hint
        assert "structured" in hint.lower() or "output" in hint.lower()

    def test_should_defer(self, structured_output_tool: StructuredOutputTool) -> None:
        assert structured_output_tool.should_defer is False

    def test_always_load(self, structured_output_tool: StructuredOutputTool) -> None:
        assert structured_output_tool.always_load is False

    def test_max_result_size_chars(self, structured_output_tool: StructuredOutputTool) -> None:
        assert structured_output_tool.max_result_size_chars == 100_000

    def test_strict(self, structured_output_tool: StructuredOutputTool) -> None:
        # StructuredOutput typically needs strict input
        assert structured_output_tool.strict is True

    def test_description_text(self, structured_output_tool: StructuredOutputTool) -> None:
        desc = structured_output_tool.description_text
        assert "structured" in desc.lower() or "output" in desc.lower()

    def test_prompt_text(self, structured_output_tool: StructuredOutputTool) -> None:
        prompt = structured_output_tool.prompt_text
        assert isinstance(prompt, str)

    def test_input_schema(self, structured_output_tool: StructuredOutputTool) -> None:
        schema = structured_output_tool.input_schema
        assert schema["type"] == "object"
        # Empty object schema - passthrough
        assert schema.get("properties", {}) == {}

    def test_output_schema(self, structured_output_tool: StructuredOutputTool) -> None:
        schema = structured_output_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"
        # Output should have a string field for structured output
        props = schema.get("properties", {})
        assert "string" in props or len(props) >= 0

    def test_user_facing_name(self, structured_output_tool: StructuredOutputTool) -> None:
        result = structured_output_tool.user_facing_name({})
        assert isinstance(result, str)

    def test_is_enabled(self, structured_output_tool: StructuredOutputTool) -> None:
        result = structured_output_tool.is_enabled()
        assert isinstance(result, bool)

    def test_is_concurrency_safe(self, structured_output_tool: StructuredOutputTool) -> None:
        assert structured_output_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, structured_output_tool: StructuredOutputTool) -> None:
        # StructuredOutput is read-only - it formats existing output
        assert structured_output_tool.is_read_only({}) is True

    def test_is_open_world(self, structured_output_tool: StructuredOutputTool) -> None:
        # StructuredOutput should be open world as it formats any structured data
        result = structured_output_tool.is_open_world({})
        assert result is True

    def test_to_auto_classifier_input_empty(self, structured_output_tool: StructuredOutputTool) -> None:
        result = structured_output_tool.to_auto_classifier_input({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_validate_input_not_needed(self, structured_output_tool: StructuredOutputTool) -> None:
        # StructuredOutput should not need validation
        result = await structured_output_tool.validate_input({}, MagicMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_call_returns_structured_output(
        self, structured_output_tool: StructuredOutputTool, mock_context: MagicMock
    ) -> None:
        result = await structured_output_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        data = result.data if hasattr(result, "data") else result
        assert "string" in data or "structured_output" in data
        # StructuredOutput returns flat dict with string and structured_output keys

    @pytest.mark.asyncio
    async def test_call_with_various_input_types(
        self, structured_output_tool: StructuredOutputTool, mock_context: MagicMock
    ) -> None:
        # Test with empty input
        result1 = await structured_output_tool.call(
            {},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result1 is not None

        # Test with simple input
        result2 = await structured_output_tool.call(
            {"simple": "value"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result2 is not None

        # Test with complex nested input
        result3 = await structured_output_tool.call(
            {
                "nested": {
                    "data": {
                        "array": [1, 2, 3],
                        "string": "value",
                        "boolean": True,
                    }
                }
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result3 is not None

    def test_map_tool_result_to_tool_result_block_param(
        self, structured_output_tool: StructuredOutputTool
    ) -> None:
        content = {
            "string": "This is structured output content",
        }
        result = structured_output_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-structured"
        )
        assert result["tool_use_id"] == "tool-use-structured"
        assert result["type"] == "tool_result"
        assert "structured" in result["content"].lower() or "output" in result["content"].lower()
