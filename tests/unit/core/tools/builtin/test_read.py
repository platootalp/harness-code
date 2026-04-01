"""Unit tests for ReadFileTool."""

import os
import tempfile

import pytest

from mozi.core.tools.builtin.read import ReadFileTool
from mozi.core.tools.framework import ToolContext, ToolStatus


class TestReadFileTool:
    """Tests for ReadFileTool."""

    def test_read_tool_initialization(self) -> None:
        """Test ReadFileTool initializes correctly."""
        tool = ReadFileTool()
        assert tool.name == "read"

    def test_read_tool_schema(self) -> None:
        """Test ReadFileTool schema includes path, limit, offset."""
        tool = ReadFileTool()
        schema = tool.schema
        assert "path" in schema["parameters"]["properties"]
        assert "limit" in schema["parameters"]["properties"]
        assert "offset" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_read_tool_denied_insufficient_permission(self) -> None:
        """Test read tool is denied with low permission level."""
        tool = ReadFileTool()
        context = ToolContext(
            tool_name="read",
            parameters={"path": "/some/file"},
            permission_level=0,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED

    @pytest.mark.asyncio
    async def test_read_tool_denied_path_not_in_whitelist(self) -> None:
        """Test read tool denies path outside whitelist."""
        tool = ReadFileTool()
        context = ToolContext(
            tool_name="read",
            parameters={"path": "/etc/passwd"},
            permission_level=1,
            allowed_paths=["/Users/lijunyi/road/mozi"],
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED
        assert "not within allowed paths" in result.error

    @pytest.mark.asyncio
    async def test_read_tool_reads_file(self) -> None:
        """Test read tool successfully reads a file."""
        tool = ReadFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Hello, World!")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="read",
                parameters={"path": temp_path},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "Hello, World!" in result.output
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_tool_file_not_found(self) -> None:
        """Test read tool handles missing file."""
        tool = ReadFileTool()
        context = ToolContext(
            tool_name="read",
            parameters={"path": "/nonexistent/file.txt"},
            permission_level=1,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.FAILURE
        assert "not found" in result.error.lower()
