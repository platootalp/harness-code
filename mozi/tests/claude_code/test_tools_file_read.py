"""
Tests for FileReadTool.

These tests verify the FileReadTool implementation works correctly.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_code.tools.file_read import (
    BLOCKED_DEVICE_PATHS,
    FILE_READ_TOOL_NAME,
    FileReadTool,
)


@pytest.fixture
def file_read_tool() -> FileReadTool:
    return FileReadTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.read_file_state = None
    return ctx


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test text files
        with open(os.path.join(tmpdir, "simple.txt"), "w") as f:
            f.write("line 1\nline 2\nline 3\n")

        with open(os.path.join(tmpdir, "multiline.txt"), "w") as f:
            for i in range(100):
                f.write(f"line {i}\n")

        with open(os.path.join(tmpdir, "unicode.txt"), "w", encoding="utf-8") as f:
            f.write("hello 你好 world 🌍\n")

        # Create a test image (small PNG)
        with open(os.path.join(tmpdir, "image.png"), "wb") as f:
            # Minimal 1x1 transparent PNG
            f.write(
                b"\x89PNG\r\n\x1a\n"
                b"\x00\x00\x00\rIHDR"
                b"\x00\x00\x00\x01"
                b"\x00\x00\x00\x01"
                b"\x08\x06\x00\x00\x00"
                b"\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDAT"
                b"\x08\x99c\xf8\x0f\x00"
                b"\x00\x01\x00\x01\x00"
                b"\x18\xdd\x8d\xb4"
                b"\x00\x00\x00\x00IEND"
                b"\xaeB`\x82"
            )

        # Create a test Jupyter notebook
        with open(os.path.join(tmpdir, "notebook.ipynb"), "w") as f:
            json.dump({
                "cells": [
                    {
                        "cell_type": "code",
                        "source": ["print('hello world')"],
                    },
                    {
                        "cell_type": "markdown",
                        "source": ["# Title"],
                    },
                ],
                "metadata": {},
            }, f)

        yield tmpdir


class TestFileReadTool:
    def test_name(self, file_read_tool: FileReadTool) -> None:
        assert file_read_tool.name == FILE_READ_TOOL_NAME

    def test_input_schema(self, file_read_tool: FileReadTool) -> None:
        schema = file_read_tool.input_schema
        assert schema["type"] == "object"
        assert "file_path" in schema["required"]
        assert "file_path" in schema["properties"]
        assert "offset" in schema["properties"]
        assert "limit" in schema["properties"]

    def test_is_concurrency_safe(self, file_read_tool: FileReadTool) -> None:
        assert file_read_tool.is_concurrency_safe({}) is True

    def test_is_read_only(self, file_read_tool: FileReadTool) -> None:
        assert file_read_tool.is_read_only({}) is True

    def test_is_read_command(self, file_read_tool: FileReadTool) -> None:
        result = file_read_tool.is_search_or_read_command({})
        assert result["is_search"] is False
        assert result["is_read"] is True

    def test_get_path(self, file_read_tool: FileReadTool) -> None:
        path = file_read_tool.get_path({"file_path": "/some/path.txt"})
        assert path == os.path.abspath("/some/path.txt")

    def test_to_auto_classifier_input(self, file_read_tool: FileReadTool) -> None:
        result = file_read_tool.to_auto_classifier_input({"file_path": "/path/to/file.py"})
        assert result == "/path/to/file.py"

    @pytest.mark.asyncio
    async def test_validate_input_missing_path(
        self, file_read_tool: FileReadTool, mock_context: MagicMock
    ) -> None:
        result = await file_read_tool.validate_input({}, mock_context)
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 400

    @pytest.mark.asyncio
    async def test_validate_input_blocked_device(
        self, file_read_tool: FileReadTool, mock_context: MagicMock
    ) -> None:
        result = await file_read_tool.validate_input(
            {"file_path": "/dev/zero"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 403

    @pytest.mark.asyncio
    async def test_validate_input_unc_path(
        self, file_read_tool: FileReadTool, mock_context: MagicMock
    ) -> None:
        result = await file_read_tool.validate_input(
            {"file_path": "\\\\server\\share\\file.txt"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 403

    @pytest.mark.asyncio
    async def test_validate_input_nonexistent_file(
        self, file_read_tool: FileReadTool, mock_context: MagicMock
    ) -> None:
        result = await file_read_tool.validate_input(
            {"file_path": "/nonexistent/file.txt"}, mock_context
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 404

    @pytest.mark.asyncio
    async def test_call_simple_text_file(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "simple.txt")},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "text"
        assert result.data.num_lines == 4
        assert result.data.lines is not None
        assert "line 1" in result.data.lines[0]

    @pytest.mark.asyncio
    async def test_call_with_offset(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "simple.txt"), "offset": 1},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "text"
        assert result.data.num_lines == 3
        assert result.data.offset == 1

    @pytest.mark.asyncio
    async def test_call_with_limit(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "simple.txt"), "limit": 1},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "text"
        assert result.data.num_lines == 1
        assert result.data.limit == 1

    @pytest.mark.asyncio
    async def test_call_with_offset_and_limit(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "simple.txt"), "offset": 1, "limit": 1},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "text"
        assert result.data.num_lines == 1
        assert result.data.lines[0] == "line 2"

    @pytest.mark.asyncio
    async def test_call_unicode_file(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "unicode.txt")},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "text"
        assert result.data.encoding == "utf-8"

    @pytest.mark.asyncio
    async def test_call_image_file(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "image.png")},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "image"
        assert result.data.base64_image is not None
        assert result.data.image_format == "png"

    @pytest.mark.asyncio
    async def test_call_notebook(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "notebook.ipynb")},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.type == "notebook"
        assert result.data.notebook_cells is not None
        assert len(result.data.notebook_cells) == 2

    @pytest.mark.asyncio
    async def test_call_file_metadata(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "simple.txt")},
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data.file_path is not None
        assert result.data.file_size is not None
        assert result.data.file_modified is not None

    @pytest.mark.asyncio
    async def test_call_nonexistent_file(
        self, file_read_tool: FileReadTool, mock_context: MagicMock, temp_dir: str
    ) -> None:
        result = await file_read_tool.call(
            {"file_path": os.path.join(temp_dir, "nonexistent.txt")},
            mock_context,
            AsyncMock(),
            None,
        )
        assert "Error" in result.data.content or result.data.type == "text"

    @pytest.mark.asyncio
    async def test_call_description_text(
        self, file_read_tool: FileReadTool
    ) -> None:
        desc = await file_read_tool.description({"file_path": "/path/to/file.py"}, {})
        assert "file" in desc.lower()

    @pytest.mark.asyncio
    async def test_call_description_pdf(
        self, file_read_tool: FileReadTool
    ) -> None:
        desc = await file_read_tool.description({"file_path": "/path/to/file.pdf"}, {})
        assert "PDF" in desc
