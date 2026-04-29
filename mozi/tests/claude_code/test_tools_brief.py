"""
Tests for BriefTool.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.brief import BriefTool


@pytest.fixture
def brief_tool() -> BriefTool:
    return BriefTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


class TestBriefTool:
    """Tests for BriefTool."""

    def test_name(self, brief_tool: BriefTool) -> None:
        assert brief_tool.name == "Brief"

    def test_aliases(self, brief_tool: BriefTool) -> None:
        assert brief_tool.aliases == ["SendUserMessage"]

    def test_search_hint(self, brief_tool: BriefTool) -> None:
        assert "message" in brief_tool.search_hint.lower()
        assert "user" in brief_tool.search_hint.lower()

    def test_should_defer(self, brief_tool: BriefTool) -> None:
        assert brief_tool.should_defer is True

    def test_always_load(self, brief_tool: BriefTool) -> None:
        assert brief_tool.always_load is False

    def test_max_result_size_chars(self, brief_tool: BriefTool) -> None:
        assert brief_tool.max_result_size_chars == 100_000

    def test_strict(self, brief_tool: BriefTool) -> None:
        assert brief_tool.strict is False

    def test_description_text(self, brief_tool: BriefTool) -> None:
        assert "message" in brief_tool.description_text.lower()

    def test_prompt_text(self, brief_tool: BriefTool) -> None:
        assert "message" in brief_tool.prompt_text.lower()

    def test_input_schema(self, brief_tool: BriefTool) -> None:
        schema = brief_tool.input_schema
        assert schema["type"] == "object"
        assert "message" in schema["required"]
        props = schema["properties"]
        assert "message" in props
        assert "attachments" in props
        assert "status" in props

    def test_output_schema(self, brief_tool: BriefTool) -> None:
        schema = brief_tool.output_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "message" in props
        assert "sentAt" in props

    def test_user_facing_name(self, brief_tool: BriefTool) -> None:
        assert brief_tool.user_facing_name({}) == ""

    def test_is_enabled(self, brief_tool: BriefTool) -> None:
        assert brief_tool.is_enabled() is True

    def test_is_concurrency_safe(self, brief_tool: BriefTool) -> None:
        assert brief_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, brief_tool: BriefTool) -> None:
        assert brief_tool.is_read_only({}) is True

    def test_to_auto_classifier_input(self, brief_tool: BriefTool) -> None:
        result = brief_tool.to_auto_classifier_input({"message": "Hello world"})
        assert result == "Hello world"

    def test_to_auto_classifier_input_empty(self, brief_tool: BriefTool) -> None:
        result = brief_tool.to_auto_classifier_input({})
        assert result == ""

    def test_validate_input_missing_message(self, brief_tool: BriefTool) -> None:
        result = brief_tool.validate_input({}, MagicMock())
        # No validation error for missing message - tool handles required via schema
        assert result is True

    def test_validate_input_attachment_exists(
        self, brief_tool: BriefTool
    ) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = f.name
        try:
            result = brief_tool.validate_input({"attachments": [temp_path]}, MagicMock())
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_validate_input_attachment_missing(self, brief_tool: BriefTool) -> None:
        result = brief_tool.validate_input(
            {"attachments": ["/nonexistent/file.txt"]}, MagicMock()
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert "not found" in result[1]

    @pytest.mark.asyncio
    async def test_call_simple_message(
        self, brief_tool: BriefTool, mock_context: MagicMock
    ) -> None:
        result = await brief_tool.call(
            {"message": "Hello world"}, mock_context, AsyncMock(), None
        )
        assert result["data"]["message"] == "Hello world"
        assert "sentAt" in result["data"]

    @pytest.mark.asyncio
    async def test_call_with_status(
        self, brief_tool: BriefTool, mock_context: MagicMock
    ) -> None:
        result = await brief_tool.call(
            {"message": "Proactive update", "status": "proactive"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result["data"]["message"] == "Proactive update"

    @pytest.mark.asyncio
    async def test_call_with_attachments(
        self, brief_tool: BriefTool, mock_context: MagicMock
    ) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            temp_path = f.name

        try:
            result = await brief_tool.call(
                {"message": "With file", "attachments": [temp_path]},
                mock_context,
                AsyncMock(),
                None,
            )
            assert result["data"]["message"] == "With file"
            assert "attachments" in result["data"]
            attachments = result["data"]["attachments"]
            assert len(attachments) == 1
            assert attachments[0]["path"] == temp_path
            assert attachments[0]["size"] > 0
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_call_image_detection(
        self, brief_tool: BriefTool, mock_context: MagicMock
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png")
            temp_path = f.name

        try:
            result = await brief_tool.call(
                {"message": "Screenshot", "attachments": [temp_path]},
                mock_context,
                AsyncMock(),
                None,
            )
            attachments = result["data"]["attachments"]
            assert attachments[0]["isImage"] is True
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_call_missing_attachments_ignored(
        self, brief_tool: BriefTool, mock_context: MagicMock
    ) -> None:
        result = await brief_tool.call(
            {"message": "File missing", "attachments": ["/nonexistent/file.txt"]},
            mock_context,
            AsyncMock(),
            None,
        )
        # Non-existent files are skipped from resolved list
        assert result["data"]["message"] == "File missing"
        assert result["data"]["attachments"] == []

    def test_map_tool_result_no_attachments(self, brief_tool: BriefTool) -> None:
        result = brief_tool.map_tool_result_to_tool_result_block_param(
            {"message": "Hello"}, "tool-123"
        )
        assert result["tool_use_id"] == "tool-123"
        assert result["type"] == "tool_result"
        assert "delivered" in result["content"].lower()
        assert "attachment" not in result["content"]

    def test_map_tool_result_with_attachments(self, brief_tool: BriefTool) -> None:
        result = brief_tool.map_tool_result_to_tool_result_block_param(
            {
                "message": "Hello",
                "attachments": [
                    {"path": "/a.txt", "size": 100, "isImage": False},
                    {"path": "/b.txt", "size": 200, "isImage": False},
                ],
            },
            "tool-456",
        )
        assert "2 attachments" in result["content"]

    def test_map_tool_result_single_attachment(self, brief_tool: BriefTool) -> None:
        result = brief_tool.map_tool_result_to_tool_result_block_param(
            {
                "message": "Hello",
                "attachments": [{"path": "/a.txt", "size": 100, "isImage": False}],
            },
            "tool-789",
        )
        assert "1 attachment" in result["content"]
