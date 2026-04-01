"""Unit tests for GrepTool."""

import os
import tempfile

import pytest

from mozi.core.tools.builtin.grep import GrepTool
from mozi.core.tools.framework import ToolContext, ToolStatus


class TestGrepTool:
    """Tests for GrepTool."""

    def test_grep_tool_initialization(self) -> None:
        """Test GrepTool initializes correctly."""
        tool = GrepTool()
        assert tool.name == "grep"

    def test_grep_tool_schema(self) -> None:
        """Test GrepTool schema includes pattern, path, etc."""
        tool = GrepTool()
        schema = tool.schema
        assert "pattern" in schema["parameters"]["properties"]
        assert "path" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_grep_tool_denied_insufficient_permission(self) -> None:
        """Test grep tool is denied with low permission level."""
        tool = GrepTool()
        context = ToolContext(
            tool_name="grep",
            parameters={"pattern": "test", "path": "/some/path"},
            permission_level=0,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED

    @pytest.mark.asyncio
    async def test_grep_tool_finds_match(self) -> None:
        """Test grep tool finds matches in file."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, "w") as f:
                f.write("def hello():\n    return 'world'\n")

            context = ToolContext(
                tool_name="grep",
                parameters={"pattern": "hello", "path": file_path},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_no_matches(self) -> None:
        """Test grep tool handles no matches."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, "w") as f:
                f.write("def hello():\n    return 'world'\n")

            context = ToolContext(
                tool_name="grep",
                parameters={"pattern": "nonexistent", "path": file_path},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "No matches found" in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_invalid_regex(self) -> None:
        """Test grep tool handles invalid regex."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, "w") as f:
                f.write("some content")

            context = ToolContext(
                tool_name="grep",
                parameters={"pattern": "[invalid", "path": file_path},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.FAILURE
            assert "Invalid regex" in result.error
