"""Unit tests for EditFileTool."""

import os
import tempfile

import pytest

from mozi.core.tools.builtin.edit import EditFileTool
from mozi.core.tools.framework import ToolContext, ToolStatus


class TestEditFileTool:
    """Tests for EditFileTool."""

    def test_edit_tool_initialization(self) -> None:
        """Test EditFileTool initializes correctly."""
        tool = EditFileTool()
        assert tool.name == "edit"

    def test_edit_tool_schema(self) -> None:
        """Test EditFileTool schema includes path, old_string, new_string."""
        tool = EditFileTool()
        schema = tool.schema
        assert "path" in schema["parameters"]["properties"]
        assert "old_string" in schema["parameters"]["properties"]
        assert "new_string" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_edit_tool_denied_insufficient_permission(self) -> None:
        """Test edit tool is denied with low permission level."""
        tool = EditFileTool()
        context = ToolContext(
            tool_name="edit",
            parameters={"path": "/some/file", "old_string": "a", "new_string": "b"},
            permission_level=1,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED

    @pytest.mark.asyncio
    async def test_edit_tool_replaces_string(self) -> None:
        """Test edit tool successfully replaces a string."""
        tool = EditFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Hello, World!")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="edit",
                parameters={
                    "path": temp_path,
                    "old_string": "World",
                    "new_string": "Mozi",
                },
                permission_level=2,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            with open(temp_path) as f:
                assert f.read() == "Hello, Mozi!"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_tool_string_not_found(self) -> None:
        """Test edit tool handles missing string."""
        tool = EditFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Hello, World!")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="edit",
                parameters={
                    "path": temp_path,
                    "old_string": "NonExistent",
                    "new_string": "Mozi",
                },
                permission_level=2,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.FAILURE
            assert "not found" in result.error.lower()
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_edit_tool_uses_regex(self) -> None:
        """Test edit tool with regex replacement."""
        tool = EditFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("item1 item2 item3")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="edit",
                parameters={
                    "path": temp_path,
                    "old_string": r"item\d",
                    "new_string": "NEW",
                    "use_regex": True,
                },
                permission_level=2,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            with open(temp_path) as f:
                content = f.read()
                assert "NEW" in content
        finally:
            os.unlink(temp_path)
