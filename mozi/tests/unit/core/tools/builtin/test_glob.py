"""Unit tests for GlobTool."""

import os
import tempfile

import pytest

from mozi.core.tools.builtin.glob import GlobTool
from mozi.core.tools.framework import ToolContext, ToolStatus


class TestGlobTool:
    """Tests for GlobTool."""

    def test_glob_tool_initialization(self) -> None:
        """Test GlobTool initializes correctly."""
        tool = GlobTool()
        assert tool.name == "glob"

    def test_glob_tool_schema(self) -> None:
        """Test GlobTool schema includes pattern, path."""
        tool = GlobTool()
        schema = tool.schema
        assert "pattern" in schema["parameters"]["properties"]
        assert "path" in schema["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_glob_tool_denied_insufficient_permission(self) -> None:
        """Test glob tool is denied with low permission level."""
        tool = GlobTool()
        context = ToolContext(
            tool_name="glob",
            parameters={"pattern": "*.py", "path": "/some/path"},
            permission_level=0,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.DENIED

    @pytest.mark.asyncio
    async def test_glob_tool_finds_files(self) -> None:
        """Test glob tool finds matching files."""
        tool = GlobTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some Python files
            os.makedirs(os.path.join(tmpdir, "subdir"))
            with open(os.path.join(tmpdir, "file1.py"), "w") as f:
                f.write("# file 1")
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("# file 2")
            with open(os.path.join(tmpdir, "file3.txt"), "w") as f:
                f.write("# text file")

            context = ToolContext(
                tool_name="glob",
                parameters={"pattern": "*.py", "path": tmpdir},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "file1.py" in result.output
            assert "file2.py" in result.output
            assert "file3.txt" not in result.output

    @pytest.mark.asyncio
    async def test_glob_tool_recursive(self) -> None:
        """Test glob tool finds files recursively."""
        tool = GlobTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested files
            os.makedirs(os.path.join(tmpdir, "subdir", "nested"))
            with open(os.path.join(tmpdir, "top.py"), "w") as f:
                f.write("# top")
            with open(os.path.join(tmpdir, "subdir", "middle.py"), "w") as f:
                f.write("# middle")
            with open(
                os.path.join(tmpdir, "subdir", "nested", "deep.py"), "w"
            ) as f:
                f.write("# deep")

            context = ToolContext(
                tool_name="glob",
                parameters={"pattern": "*.py", "path": tmpdir, "recursive": True},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "top.py" in result.output
            assert "middle.py" in result.output
            assert "deep.py" in result.output

    @pytest.mark.asyncio
    async def test_glob_tool_no_matches(self) -> None:
        """Test glob tool handles no matches."""
        tool = GlobTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            context = ToolContext(
                tool_name="glob",
                parameters={"pattern": "*.py", "path": tmpdir},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "No matches found" in result.output
