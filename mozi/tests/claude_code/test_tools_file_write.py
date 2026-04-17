"""
Tests for FileWriteTool.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.file_write import (
    FILE_WRITE_TOOL_NAME,
    FileWriteTool,
    FileWriteToolOutput,
)


@pytest.fixture
def file_write_tool() -> FileWriteTool:
    return FileWriteTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestFileWriteTool:
    """Tests for FileWriteTool."""

    def test_name(self, file_write_tool: FileWriteTool) -> None:
        assert file_write_tool.name == FILE_WRITE_TOOL_NAME

    def test_input_schema(self, file_write_tool: FileWriteTool) -> None:
        schema = file_write_tool.input_schema
        assert schema["type"] == "object"
        assert "file_path" in schema["required"]
        assert "content" in schema["required"]
        assert "file_path" in schema["properties"]
        assert "content" in schema["properties"]

    def test_is_concurrency_safe(self, file_write_tool: FileWriteTool) -> None:
        assert file_write_tool.is_concurrency_safe({}) is False

    def test_is_read_only(self, file_write_tool: FileWriteTool) -> None:
        assert file_write_tool.is_read_only({}) is False

    def test_is_destructive(self, file_write_tool: FileWriteTool) -> None:
        assert file_write_tool.is_destructive({}) is True

    def test_get_path(self, file_write_tool: FileWriteTool) -> None:
        path = file_write_tool.get_path({"file_path": "/some/file.py"})
        assert path == "/some/file.py"

    def test_to_auto_classifier_input(self, file_write_tool: FileWriteTool) -> None:
        result = file_write_tool.to_auto_classifier_input(
            {"file_path": "/path/file.py"}
        )
        assert result == "/path/file.py"

    def test_max_result_size_chars(self, file_write_tool: FileWriteTool) -> None:
        assert file_write_tool.max_result_size_chars == 100_000

    def test_strict(self, file_write_tool: FileWriteTool) -> None:
        assert file_write_tool.strict is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_path(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock
    ) -> None:
        result = await file_write_tool.validate_input(
            {"content": "hello"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_missing_content(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock
    ) -> None:
        result = await file_write_tool.validate_input(
            {"file_path": "/tmp/f"}, mock_context
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_parent_not_exists(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock
    ) -> None:
        result = await file_write_tool.validate_input(
            {"file_path": "/nonexistent/parent/file.txt", "content": "hello"},
            mock_context,
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_valid_new(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_write_tool.validate_input(
            {"file_path": os.path.join(temp_dir, "new.txt"), "content": "hello"},
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_input_valid_existing(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "existing.txt")
        with open(file_path, "w") as f:
            f.write("old content")

        result = await file_write_tool.validate_input(
            {"file_path": file_path, "content": "new content"},
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_create_new_file(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "new_file.txt")

        result = await file_write_tool.call(
            {"file_path": file_path, "content": "hello world"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, FileWriteToolOutput)
        assert result.data.type == "create"
        assert result.data.file_path == file_path
        assert result.data.content == "hello world"

    @pytest.mark.asyncio
    async def test_call_overwrite_existing_file(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "existing.txt")
        with open(file_path, "w") as f:
            f.write("old content")

        result = await file_write_tool.call(
            {"file_path": file_path, "content": "new content"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "update"
        assert result.data.original_file == "old content"

    @pytest.mark.asyncio
    async def test_call_creates_diff(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "existing.txt")
        with open(file_path, "w") as f:
            f.write("old content")

        result = await file_write_tool.call(
            {"file_path": file_path, "content": "new content"},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.git_diff is not None
        assert len(result.data.structured_patch) > 0

    @pytest.mark.asyncio
    async def test_call_no_diff_for_identical_content(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "existing.txt")
        content = "same content"
        with open(file_path, "w") as f:
            f.write(content)

        result = await file_write_tool.call(
            {"file_path": file_path, "content": content},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.git_diff is None
        assert result.data.structured_patch == []

    @pytest.mark.asyncio
    async def test_call_file_actually_written(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "new.txt")

        await file_write_tool.call(
            {"file_path": file_path, "content": "written content"},
            mock_context,
            AsyncMock(),
            None,
        )

        with open(file_path) as f:
            assert f.read() == "written content"

    @pytest.mark.asyncio
    async def test_call_preserves_crlf(
        self, file_write_tool: FileWriteTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "crlf.txt")
        with open(file_path, "w", newline="") as f:
            f.write("line1\r\nline2\r\n")

        await file_write_tool.call(
            {"file_path": file_path, "content": "line1\nline2\n"},
            mock_context,
            AsyncMock(),
            None,
        )

        with open(file_path, "rb") as f:
            content = f.read()
        assert b"\r\n" in content

    @pytest.mark.asyncio
    async def test_description(self, file_write_tool: FileWriteTool) -> None:
        desc = await file_write_tool.description({}, {})
        assert "write" in desc.lower() or "file" in desc.lower()

    @pytest.mark.asyncio
    async def test_prompt(self, file_write_tool: FileWriteTool) -> None:
        prompt = await file_write_tool.prompt({})
        assert "Write" in prompt or "file" in prompt.lower()


class TestFileWriteToolOutput:
    """Tests for FileWriteToolOutput dataclass."""

    def test_output_create_type(self) -> None:
        output = FileWriteToolOutput(
            type="create",
            file_path="/tmp/test.txt",
            content="hello",
            structured_patch=[],
            original_file=None,
        )
        assert output.type == "create"
        assert output.original_file is None

    def test_output_update_type(self) -> None:
        output = FileWriteToolOutput(
            type="update",
            file_path="/tmp/test.txt",
            content="new",
            structured_patch=[],
            original_file="old",
        )
        assert output.type == "update"
        assert output.original_file == "old"
