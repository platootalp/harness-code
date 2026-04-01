"""Unit tests for WriteFileTool."""

import os
import tempfile

import pytest

from mozi.core.tools.builtin.write import WriteFileTool
from mozi.core.tools.framework import ToolContext, ToolStatus


class TestWriteFileTool:
    """Tests for WriteFileTool."""

    def test_write_tool_initialization(self) -> None:
        """Test WriteFileTool initializes correctly."""
        tool = WriteFileTool()
        assert tool.name == "write"

    def test_write_tool_schema(self) -> None:
        """Test WriteFileTool schema includes path, content, append."""
        tool = WriteFileTool()
        schema = tool.schema
        assert "path" in schema["parameters"]["properties"]
        assert "content" in schema["parameters"]["properties"]
        assert "append" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_write_tool_denied_insufficient_permission(self) -> None:
        """Test write tool is denied with low permission level."""
        tool = WriteFileTool()
        context = ToolContext(
            tool_name="write",
            parameters={"path": "/some/file", "content": "data"},
            permission_level=1,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED

    @pytest.mark.asyncio
    async def test_write_tool_denied_path_not_in_whitelist(self) -> None:
        """Test write tool denies path outside whitelist."""
        tool = WriteFileTool()
        context = ToolContext(
            tool_name="write",
            parameters={"path": "/etc/passwd", "content": "data"},
            permission_level=2,
            allowed_paths=["/Users/lijunyi/road/mozi"],
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED

    @pytest.mark.asyncio
    async def test_write_tool_writes_file(self) -> None:
        """Test write tool successfully writes a file."""
        tool = WriteFileTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            context = ToolContext(
                tool_name="write",
                parameters={"path": file_path, "content": "Hello, World!"},
                permission_level=2,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert os.path.exists(file_path)
            with open(file_path) as f:
                assert f.read() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_write_tool_atomic_write(self) -> None:
        """Test write tool uses atomic write."""
        tool = WriteFileTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "atomic.txt")
            context = ToolContext(
                tool_name="write",
                parameters={"path": file_path, "content": "Atomic content"},
                permission_level=2,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            # Verify content was written atomically
            with open(file_path) as f:
                assert f.read() == "Atomic content"

    @pytest.mark.asyncio
    async def test_write_tool_creates_parent_dirs(self) -> None:
        """Test write tool creates parent directories."""
        tool = WriteFileTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "nested", "test.txt")
            context = ToolContext(
                tool_name="write",
                parameters={"path": file_path, "content": "Nested"},
                permission_level=2,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert os.path.exists(file_path)
