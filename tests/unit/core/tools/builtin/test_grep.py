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
    async def test_grep_tool_denied_path_not_in_whitelist(self) -> None:
        """Test grep tool denies path outside whitelist."""
        tool = GrepTool()
        context = ToolContext(
            tool_name="grep",
            parameters={"pattern": "test", "path": "/etc/passwd"},
            permission_level=1,
            allowed_paths=["/Users/lijunyi/road/mozi"],
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

    @pytest.mark.asyncio
    async def test_grep_tool_case_insensitive(self) -> None:
        """Test grep tool case insensitive matching."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, "w") as f:
                f.write("def HELLO():\n    return 'world'\n")

            context = ToolContext(
                tool_name="grep",
                parameters={
                    "pattern": "hello",
                    "path": file_path,
                    "case_sensitive": False,
                },
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "HELLO" in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_without_line_numbers(self) -> None:
        """Test grep tool without line numbers in output."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")
            with open(file_path, "w") as f:
                f.write("def hello():\n    return 'world'\n")

            context = ToolContext(
                tool_name="grep",
                parameters={
                    "pattern": "hello",
                    "path": file_path,
                    "line_numbers": False,
                },
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            # Output should be filepath:content without line number
            # The format is "filepath:line_content", so it should contain the filepath
            assert file_path in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_directory_non_recursive(self) -> None:
        """Test grep tool searches only top-level files in directory."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            # Create file at top level
            file_path = os.path.join(tmpdir, "toplevel.py")
            with open(file_path, "w") as f:
                f.write("TOPLEVEL_VAR = 'found'\n")

            # Create file in subdirectory (should not be found)
            nested_file = os.path.join(subdir, "nested.py")
            with open(nested_file, "w") as f:
                f.write("NESTED_VAR = 'hidden'\n")

            context = ToolContext(
                tool_name="grep",
                parameters={"pattern": "TOPLEVEL_VAR", "path": tmpdir, "recursive": False},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "TOPLEVEL_VAR" in result.output
            assert "NESTED_VAR" not in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_directory_recursive(self) -> None:
        """Test grep tool searches recursively in directory."""
        tool = GrepTool()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            # Create file at top level
            file_path = os.path.join(tmpdir, "toplevel.py")
            with open(file_path, "w") as f:
                f.write("TOPLEVEL_VAR = 'found'\n")

            # Create file in subdirectory
            nested_file = os.path.join(subdir, "nested.py")
            with open(nested_file, "w") as f:
                f.write("NESTED_VAR = 'also found'\n")

            context = ToolContext(
                tool_name="grep",
                parameters={"pattern": "found", "path": tmpdir, "recursive": True},
                permission_level=1,
            )
            result = await tool.execute(context)
            assert result.status == ToolStatus.SUCCESS
            assert "TOPLEVEL_VAR" in result.output
            assert "NESTED_VAR" in result.output

    @pytest.mark.asyncio
    async def test_grep_tool_invalid_path(self) -> None:
        """Test grep tool handles invalid path."""
        tool = GrepTool()
        context = ToolContext(
            tool_name="grep",
            parameters={"pattern": "test", "path": "/nonexistent/path"},
            permission_level=1,
        )
        result = await tool.execute(context)
        assert result.status == ToolStatus.FAILURE
        assert "Invalid path" in result.error
