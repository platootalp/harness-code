"""
Tests for GlobTool.

These tests verify the GlobTool implementation works correctly.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.glob import GlobTool


@pytest.fixture
def glob_tool() -> GlobTool:
    return GlobTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.glob_limits = None
    return ctx


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        os.makedirs(os.path.join(tmpdir, "subdir"))
        open(os.path.join(tmpdir, "file1.txt"), "w").close()
        open(os.path.join(tmpdir, "file2.txt"), "w").close()
        open(os.path.join(tmpdir, "file1.py"), "w").close()
        open(os.path.join(tmpdir, "subdir", "nested.txt"), "w").close()
        yield tmpdir


class TestGlobTool:
    def test_name(self, glob_tool: GlobTool) -> None:
        assert glob_tool.name == "Glob"

    def test_input_schema(self, glob_tool: GlobTool) -> None:
        schema = glob_tool.input_schema
        assert schema["type"] == "object"
        assert "pattern" in schema["required"]
        assert "pattern" in schema["properties"]
        assert "path" in schema["properties"]

    def test_is_concurrency_safe(self, glob_tool: GlobTool) -> None:
        assert glob_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, glob_tool: GlobTool) -> None:
        assert glob_tool.is_read_only({}) is True

    def test_is_search_command(self, glob_tool: GlobTool) -> None:
        result = glob_tool.is_search_or_read_command({})
        assert result["is_search"] is True
        assert result["is_read"] is False

    def test_get_path_with_path(self, glob_tool: GlobTool) -> None:
        path = glob_tool.get_path({"path": "/some/path"})
        assert path == os.path.abspath("/some/path")

    def test_get_path_without_path(self, glob_tool: GlobTool) -> None:
        path = glob_tool.get_path({})
        assert path == os.getcwd()

    def test_to_auto_classifier_input(self, glob_tool: GlobTool) -> None:
        result = glob_tool.to_auto_classifier_input({"pattern": "*.py"})
        assert result == "*.py"

    @pytest.mark.asyncio
    async def test_validate_input_missing_pattern(
        self, glob_tool: GlobTool, mock_context: MagicMock
    ) -> None:
        result = await glob_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_invalid_path(
        self, glob_tool: GlobTool, mock_context: MagicMock
    ) -> None:
        result = await glob_tool.validate_input(
            {"pattern": "*.txt", "path": "/nonexistent/path"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_valid(self, glob_tool: GlobTool, mock_context: MagicMock) -> None:
        result = await glob_tool.validate_input({"pattern": "*.txt"}, mock_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_call_basic_glob(
        self, glob_tool: GlobTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await glob_tool.call(
            {"pattern": "*.txt", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        # *.txt matches all .txt files including in subdirectories (recursive)
        assert result.data.num_files == 3
        assert set(result.data.filenames) == {
            os.path.join(temp_dir, "file1.txt"),
            os.path.join(temp_dir, "file2.txt"),
            os.path.join(temp_dir, "subdir", "nested.txt"),
        }
        assert result.data.truncated is False

    @pytest.mark.asyncio
    async def test_call_recursive_glob(
        self, glob_tool: GlobTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await glob_tool.call(
            {"pattern": "**/*.txt", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        # **/*.txt is equivalent to *.txt - matches all .txt files recursively
        assert result.data.num_files == 3

    @pytest.mark.asyncio
    async def test_call_default_path(
        self, glob_tool: GlobTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        # Change to temp dir and search without specifying path
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            mock_context.glob_limits = None
            result = await glob_tool.call(
                {"pattern": "*.py"},
                mock_context,
                AsyncMock(),
                None,
            )
            assert result.data.num_files == 1
            assert "file1.py" in result.data.filenames[0]
        finally:
            os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_call_truncation(
        self, glob_tool: GlobTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        mock_context.glob_limits = {"max_results": 2}
        result = await glob_tool.call(
            {"pattern": "*.txt", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.truncated is True
        assert result.data.num_files == 2

    @pytest.mark.asyncio
    async def test_call_empty_result(
        self, glob_tool: GlobTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await glob_tool.call(
            {"pattern": "*.xyz", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.num_files == 0
        assert result.data.filenames == []
        assert result.data.truncated is False

    @pytest.mark.asyncio
    async def test_call_duration_reported(
        self, glob_tool: GlobTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await glob_tool.call(
            {"pattern": "*.txt", "path": temp_dir},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.duration_ms >= 0


from typing import Generator
