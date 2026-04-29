"""
Tests for tools/base.py - BaseTool and tool builder utilities.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from claude_code.models.tool import BaseTool, ToolResult


class ConcreteTool(BaseTool):
    """Concrete implementation of BaseTool for testing."""

    @property
    def name(self) -> str:
        return "TestTool"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"arg": {"type": "string"}}}

    async def call(
        self,
        args: Any,
        context: Any,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[dict[str, str]]:
        return ToolResult(data={"result": "ok"})


class TestBaseTool:
    """Tests for BaseTool abstract class."""

    @pytest.fixture
    def tool(self) -> ConcreteTool:
        return ConcreteTool()

    def test_name_property(self, tool: ConcreteTool) -> None:
        assert tool.name == "TestTool"

    def test_input_schema_property(self, tool: ConcreteTool) -> None:
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "arg" in schema["properties"]

    def test_is_enabled(self, tool: ConcreteTool) -> None:
        assert tool.is_enabled() is True

    def test_is_concurrency_safe_default(self, tool: ConcreteTool) -> None:
        assert tool.is_concurrency_safe({}) is False

    def test_is_read_only_default(self, tool: ConcreteTool) -> None:
        assert tool.is_read_only({}) is False

    def test_is_destructive_default(self, tool: ConcreteTool) -> None:
        assert tool.is_destructive({}) is False

    def test_get_path_default(self, tool: ConcreteTool) -> None:
        assert tool.get_path({}) is None

    def test_is_search_or_read_command_default(self, tool: ConcreteTool) -> None:
        result = tool.is_search_or_read_command({})
        assert result["is_search"] is False
        assert result["is_read"] is False

    def test_is_open_world_default(self, tool: ConcreteTool) -> None:
        assert tool.is_open_world({}) is False

    def test_requires_user_interaction_default(self, tool: ConcreteTool) -> None:
        assert tool.requires_user_interaction() is False

    def test_interrupt_behavior_default(self, tool: ConcreteTool) -> None:
        assert tool.interrupt_behavior() == "block"

    def test_user_facing_name_default(self, tool: ConcreteTool) -> None:
        assert tool.user_facing_name() == "TestTool"

    def test_user_facing_name_with_input(self, tool: ConcreteTool) -> None:
        assert tool.user_facing_name({"arg": "value"}) == "TestTool"

    def test_to_auto_classifier_input_default(self, tool: ConcreteTool) -> None:
        assert tool.to_auto_classifier_input({}) == ""

    @pytest.mark.asyncio
    async def test_validate_input_default(self, tool: ConcreteTool) -> None:
        result = await tool.validate_input({}, MagicMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permissions_default(self, tool: ConcreteTool) -> None:
        result = await tool.check_permissions({}, MagicMock())
        assert result.behavior == "allow"

    @pytest.mark.asyncio
    async def test_description_default(self, tool: ConcreteTool) -> None:
        result = await tool.description({}, {})
        assert result == "Tool: TestTool"

    @pytest.mark.asyncio
    async def test_prompt_default(self, tool: ConcreteTool) -> None:
        result = await tool.prompt({})
        assert result == ""

    @pytest.mark.asyncio
    async def test_call(self, tool: ConcreteTool) -> None:
        result = await tool.call({}, MagicMock(), MagicMock(), None)
        assert result.data == {"result": "ok"}

    def test_metadata_defaults(self, tool: ConcreteTool) -> None:
        assert tool.aliases is None
        assert tool.search_hint is None
        assert tool.should_defer is False
        assert tool.always_load is False
        assert tool.max_result_size_chars == 100_000
        assert tool.strict is False
