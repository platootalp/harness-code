"""
Tests for FileEditTool.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.file_edit import (
    FILE_EDIT_TOOL_NAME,
    FileEditTool,
    FileEditToolOutput,
)


@pytest.fixture
def file_edit_tool() -> FileEditTool:
    return FileEditTool()


@pytest.fixture
def mock_context() -> MagicMock:
    return MagicMock()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestFileEditTool:
    """Tests for FileEditTool."""

    def test_name(self, file_edit_tool: FileEditTool) -> None:
        assert file_edit_tool.name == FILE_EDIT_TOOL_NAME

    def test_input_schema(self, file_edit_tool: FileEditTool) -> None:
        schema = file_edit_tool.input_schema
        assert schema["type"] == "object"
        assert "file_path" in schema["required"]
        assert "old_string" in schema["required"]
        assert "new_string" in schema["required"]
        assert "file_path" in schema["properties"]
        assert "old_string" in schema["properties"]
        assert "new_string" in schema["properties"]
        assert "replace_all" in schema["properties"]

    def test_is_concurrency_safe(self, file_edit_tool: FileEditTool) -> None:
        assert file_edit_tool.is_concurrency_safe({}) is False

    def test_is_read_only(self, file_edit_tool: FileEditTool) -> None:
        assert file_edit_tool.is_read_only({}) is False

    def test_is_destructive(self, file_edit_tool: FileEditTool) -> None:
        assert file_edit_tool.is_destructive({}) is True

    def test_get_path(self, file_edit_tool: FileEditTool) -> None:
        path = file_edit_tool.get_path({"file_path": "/some/file.py"})
        assert path == "/some/file.py"

    def test_to_auto_classifier_input(self, file_edit_tool: FileEditTool) -> None:
        result = file_edit_tool.to_auto_classifier_input(
            {"file_path": "/path/file.py", "old_string": "hello"}
        )
        assert "/path/file.py" in result
        assert "hello" in result

    def test_max_result_size_chars(self, file_edit_tool: FileEditTool) -> None:
        assert file_edit_tool.max_result_size_chars == 100_000

    def test_strict(self, file_edit_tool: FileEditTool) -> None:
        assert file_edit_tool.strict is True

    @pytest.mark.asyncio
    async def test_validate_input_missing_path(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock
    ) -> None:
        result = await file_edit_tool.validate_input(
            {"old_string": "old", "new_string": "new"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_missing_old_string(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock
    ) -> None:
        result = await file_edit_tool.validate_input(
            {"file_path": "/tmp/f", "new_string": "new"}, mock_context
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_missing_new_string(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock
    ) -> None:
        result = await file_edit_tool.validate_input(
            {"file_path": "/tmp/f", "old_string": "old"}, mock_context
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_file_not_found(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock
    ) -> None:
        result = await file_edit_tool.validate_input(
            {"file_path": "/nonexistent/file.txt", "old_string": "old", "new_string": "new"},
            mock_context,
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 404

    @pytest.mark.asyncio
    async def test_validate_input_old_string_not_found(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("hello world")

        result = await file_edit_tool.validate_input(
            {"file_path": file_path, "old_string": "NOTFOUND", "new_string": "new"},
            mock_context,
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_multiple_occurrences(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("foo foo foo")

        result = await file_edit_tool.validate_input(
            {"file_path": file_path, "old_string": "foo", "new_string": "bar"},
            mock_context,
        )
        assert result is not True

    @pytest.mark.asyncio
    async def test_validate_input_replace_all_allowed(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("foo foo foo")

        result = await file_edit_tool.validate_input(
            {
                "file_path": file_path,
                "old_string": "foo",
                "new_string": "bar",
                "replace_all": True,
            },
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_simple_edit(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("hello world")

        result = await file_edit_tool.call(
            {
                "file_path": file_path,
                "old_string": "world",
                "new_string": "python",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert isinstance(result.data, FileEditToolOutput)
        assert result.data.changed is True
        assert result.data.new_content == "hello python"
        assert "world" in result.data.old_string
        assert "python" in result.data.new_string

    @pytest.mark.asyncio
    async def test_call_replace_all(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("foo foo foo")

        result = await file_edit_tool.call(
            {
                "file_path": file_path,
                "old_string": "foo",
                "new_string": "bar",
                "replace_all": True,
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.changed is True
        assert result.data.new_content == "bar bar bar"

    @pytest.mark.asyncio
    async def test_call_multiline_edit(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("line 1\nline 2\nline 3\n")

        result = await file_edit_tool.call(
            {
                "file_path": file_path,
                "old_string": "line 1\nline 2\nline 3",
                "new_string": "a\nb\nc",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.changed is True
        assert "a\nb\nc" in result.data.new_content

    @pytest.mark.asyncio
    async def test_call_file_actually_modified(
        self, file_edit_tool: FileEditTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        file_path = os.path.join(temp_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("hello")

        await file_edit_tool.call(
            {"file_path": file_path, "old_string": "hello", "new_string": "hi"},
            mock_context,
            AsyncMock(),
            None,
        )

        with open(file_path) as f:
            assert f.read() == "hi"

    @pytest.mark.asyncio
    async def test_call_description(self, file_edit_tool: FileEditTool) -> None:
        desc = await file_edit_tool.description({}, {})
        assert "edit" in desc.lower()

    @pytest.mark.asyncio
    async def test_call_prompt(self, file_edit_tool: FileEditTool) -> None:
        prompt = await file_edit_tool.prompt({})
        assert "Edit" in prompt


class TestFileEditToolOutput:
    """Tests for FileEditToolOutput dataclass."""

    def test_output_creation(self) -> None:
        output = FileEditToolOutput(
            file_path="/tmp/test.txt",
            old_string="old",
            new_string="new",
            new_content="new content",
            changed=True,
            structured_patch=[],
        )
        assert output.file_path == "/tmp/test.txt"
        assert output.old_string == "old"
        assert output.new_string == "new"
        assert output.changed is True
