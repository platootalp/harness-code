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
            allowed_paths=["/Users/lijunyi/road/src"],
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

    @pytest.mark.asyncio
    async def test_read_tool_with_offset(self) -> None:
        """Test read tool reads file from offset."""
        tool = ReadFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line1\nline2\nline3\nline4\n")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="read",
                parameters={"path": temp_path, "offset": 2},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "line3" in result.output
            assert "line1" not in result.output
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_tool_with_limit(self) -> None:
        """Test read tool limits number of lines."""
        tool = ReadFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="read",
                parameters={"path": temp_path, "limit": 2},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "line1" in result.output
            assert "line3" not in result.output
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_read_tool_with_offset_and_limit(self) -> None:
        """Test read tool reads file with both offset and limit."""
        tool = ReadFileTool()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
            temp_path = f.name

        try:
            context = ToolContext(
                tool_name="read",
                parameters={"path": temp_path, "offset": 1, "limit": 2},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "line2" in result.output
            assert "line4" not in result.output
        finally:
            os.unlink(temp_path)
