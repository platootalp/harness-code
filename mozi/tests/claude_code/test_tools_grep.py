"""
Tests for GrepTool.

These tests verify the GrepTool implementation works correctly.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.grep import GrepTool


@pytest.fixture
def grep_tool() -> GrepTool:
    return GrepTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    return ctx


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files with content
        with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
            f.write("hello world\nfoo bar\n")
        with open(os.path.join(tmpdir, "file2.txt"), "w") as f:
            f.write("hello there\nworld wide\n")
        with open(os.path.join(tmpdir, "script.py"), "w") as f:
            f.write("def hello():\n    print('hello world')\n")
        yield tmpdir


class TestGrepTool:
    def test_name(self, grep_tool: GrepTool) -> None:
        assert grep_tool.name == "Grep"

    def test_input_schema(self, grep_tool: GrepTool) -> None:
        schema = grep_tool.input_schema
        assert schema["type"] == "object"
        assert "pattern" in schema["required"]
        assert "pattern" in schema["properties"]
        assert "-i" in schema["properties"]
        assert "-n" in schema["properties"]
        assert "output_mode" in schema["properties"]

    def test_is_concurrency_safe(self, grep_tool: GrepTool) -> None:
        assert grep_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, grep_tool: GrepTool) -> None:
        assert grep_tool.is_read_only({}) is True

    def test_is_search_command(self, grep_tool: GrepTool) -> None:
        result = grep_tool.is_search_or_read_command({})
        assert result["is_search"] is True
        assert result["is_read"] is False

    def test_get_path_with_path(self, grep_tool: GrepTool) -> None:
        path = grep_tool.get_path({"path": "/some/path"})
        assert path == os.path.abspath("/some/path")

    def test_get_path_without_path(self, grep_tool: GrepTool) -> None:
        path = grep_tool.get_path({})
        assert path == os.getcwd()

    def test_to_auto_classifier_input(self, grep_tool: GrepTool) -> None:
        result = grep_tool.to_auto_classifier_input({"pattern": "hello"})
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_validate_input_missing_pattern(
        self, grep_tool: GrepTool, mock_context: MagicMock
    ) -> None:
        result = await grep_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_invalid_regex(
        self, grep_tool: GrepTool, mock_context: MagicMock
    ) -> None:
        result = await grep_tool.validate_input({"pattern": "[invalid"}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_valid(self, grep_tool: GrepTool, mock_context: MagicMock) -> None:
        result = await grep_tool.validate_input({"pattern": "hello"}, mock_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_call_files_with_matches(
        self, grep_tool: GrepTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await grep_tool.call(
            {"pattern": "hello", "path": temp_dir, "output_mode": "files_with_matches"},
            mock_context,
            AsyncMock(),
            None,
        )
        # Should find files containing "hello"
        assert result.data.num_matches >= 1
        assert result.data.output_mode == "files_with_matches"

    @pytest.mark.asyncio
    async def test_call_content_mode(
        self, grep_tool: GrepTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await grep_tool.call(
            {"pattern": "hello", "path": temp_dir, "output_mode": "content", "-n": True},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.output_mode == "content"
        assert result.data.num_matches >= 1

    @pytest.mark.asyncio
    async def test_call_no_matches(
        self, grep_tool: GrepTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await grep_tool.call(
            {"pattern": "nonexistent_xyz", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.num_matches == 0
        assert result.data.matches == []

    @pytest.mark.asyncio
    async def test_call_with_glob_filter(
        self, grep_tool: GrepTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await grep_tool.call(
            {"pattern": "hello", "path": temp_dir, "glob": "*.txt"},
            mock_context,
            AsyncMock(),
            None,
        )
        # Should only search .txt files
        assert result.data.num_matches >= 1

    @pytest.mark.asyncio
    async def test_call_duration_reported(
        self, grep_tool: GrepTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await grep_tool.call(
            {"pattern": "hello", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.duration_ms >= 0
