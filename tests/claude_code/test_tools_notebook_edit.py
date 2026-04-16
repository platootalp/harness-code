"""
Tests for NotebookEditTool.
"""

from __future__ import annotations

import json
import tempfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from claude_code.tools.notebook_edit import NotebookEditTool


@pytest.fixture
def notebook_edit_tool() -> NotebookEditTool:
    return NotebookEditTool()


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.get_app_state = MagicMock(return_value=MagicMock())
    # read_file_state returns None by default (file not read)
    mock_read_state = MagicMock()
    mock_read_state.get = MagicMock(return_value=None)
    ctx.read_file_state = mock_read_state
    return ctx


@pytest.fixture
def temp_notebook() -> str:
    with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False, mode="w") as f:
        notebook_data = {
            "nbformat": 4,
            "nbformat_minor": 4,
            "metadata": {},
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "id": "cell-1",
                    "metadata": {},
                    "outputs": [],
                    "source": ["print('hello')\n"],
                },
                {
                    "cell_type": "markdown",
                    "id": "cell-2",
                    "metadata": {},
                    "source": ["# Title\n"],
                },
            ],
        }
        json.dump(notebook_data, f)
        return f.name


class TestNotebookEditTool:
    """Tests for NotebookEditTool."""

    def test_name(self, notebook_edit_tool: NotebookEditTool) -> None:
        assert notebook_edit_tool.name == "NotebookEdit"

    def test_aliases(self, notebook_edit_tool: NotebookEditTool) -> None:
        aliases = notebook_edit_tool.aliases
        assert aliases is None or isinstance(aliases, list)

    def test_search_hint(self, notebook_edit_tool: NotebookEditTool) -> None:
        assert "notebook" in notebook_edit_tool.search_hint.lower()

    def test_should_defer(self, notebook_edit_tool: NotebookEditTool) -> None:
        # NotebookEditTool defers loading (matches TS source: shouldDefer: true)
        assert notebook_edit_tool.should_defer is True

    def test_always_load(self, notebook_edit_tool: NotebookEditTool) -> None:
        assert notebook_edit_tool.always_load is False

    def test_max_result_size_chars(self, notebook_edit_tool: NotebookEditTool) -> None:
        assert notebook_edit_tool.max_result_size_chars == 100_000

    def test_strict(self, notebook_edit_tool: NotebookEditTool) -> None:
        assert notebook_edit_tool.strict is True

    def test_description_text(self, notebook_edit_tool: NotebookEditTool) -> None:
        assert "notebook" in notebook_edit_tool.description_text.lower()

    def test_prompt_text(self, notebook_edit_tool: NotebookEditTool) -> None:
        prompt = notebook_edit_tool.prompt_text
        assert "notebook" in prompt.lower()

    def test_input_schema(self, notebook_edit_tool: NotebookEditTool) -> None:
        schema = notebook_edit_tool.input_schema
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "notebookPath" in props or "notebook_path" in props
        # notebook_path should be required
        required_fields = schema.get("required", [])
        assert any("notebook" in r.lower() for r in required_fields)
        # Optional fields
        assert "cellId" in props or "cell_id" in props
        assert "newSource" in props or "new_source" in props
        assert "cellType" in props or "cell_type" in props
        assert "editMode" in props or "edit_mode" in props

    def test_output_schema(self, notebook_edit_tool: NotebookEditTool) -> None:
        schema = notebook_edit_tool.output_schema
        assert schema is not None
        assert schema["type"] == "object"

    def test_user_facing_name(self, notebook_edit_tool: NotebookEditTool) -> None:
        result = notebook_edit_tool.user_facing_name({})
        assert isinstance(result, str)

    def test_to_auto_classifier_input(self, notebook_edit_tool: NotebookEditTool) -> None:
        result = notebook_edit_tool.to_auto_classifier_input(
            {"notebookPath": "/path/to/notebook.ipynb"}
        )
        assert "notebook.ipynb" in result or "/path/to/notebook.ipynb" in result

    @pytest.mark.asyncio
    async def test_validate_input_wrong_extension(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"# not a notebook")
            wrong_file = f.name

        try:
            result = await notebook_edit_tool.validate_input(
                {"notebookPath": wrong_file},
                mock_context,
            )
            assert result is not True
            assert isinstance(result, tuple)
            assert result[2] == 2
        finally:
            import os
            os.unlink(wrong_file)

    @pytest.mark.asyncio
    async def test_validate_input_invalid_edit_mode(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        result = await notebook_edit_tool.validate_input(
            {
                "notebookPath": temp_notebook,
                "editMode": "invalid_mode",
            },
            mock_context,
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 4

    @pytest.mark.asyncio
    async def test_validate_input_insert_without_cell_type(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        result = await notebook_edit_tool.validate_input(
            {
                "notebookPath": temp_notebook,
                "editMode": "insert",
            },
            mock_context,
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 5

    @pytest.mark.asyncio
    async def test_validate_input_file_not_read(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        # mock_context already has read_file_state returning None (file not read)

        result = await notebook_edit_tool.validate_input(
            {
                "notebookPath": temp_notebook,
                "newSource": "print('new')",
                "editMode": "replace",
            },
            mock_context,
        )
        # If file not previously read, should return error
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 9

    @pytest.mark.asyncio
    async def test_validate_input_file_modified(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        # Set up read_file_state with an old timestamp so file appears modified
        old_timestamp = MagicMock(timestamp=1000)
        mock_read_state = MagicMock()
        mock_read_state.get = MagicMock(return_value=old_timestamp)
        mock_context.read_file_state = mock_read_state

        result = await notebook_edit_tool.validate_input(
            {
                "notebookPath": temp_notebook,
                "cellId": "cell-1",
                "newSource": "print('new')",
                "editMode": "replace",
            },
            mock_context,
        )
        # If file was modified externally, should return error
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] == 10

    @pytest.mark.asyncio
    async def test_validate_input_cell_not_found(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        # Set up read_file_state to simulate file having been read
        import time
        current_timestamp = time.time()
        mock_read_state = MagicMock()
        mock_read_state.get = MagicMock(return_value=MagicMock(timestamp=current_timestamp))
        mock_context.read_file_state = mock_read_state

        result = await notebook_edit_tool.validate_input(
            {
                "notebookPath": temp_notebook,
                "cellId": "nonexistent-cell",
                "newSource": "print('new')",
                "editMode": "replace",
            },
            mock_context,
        )
        assert result is not True
        assert isinstance(result, tuple)
        assert result[2] in (7, 8)  # cell_not_found or similar

    @pytest.mark.asyncio
    async def test_validate_input_success(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        # Set up read_file_state to simulate file having been read
        import time
        current_timestamp = time.time()
        mock_read_state = MagicMock()
        mock_read_state.get = MagicMock(return_value=MagicMock(timestamp=current_timestamp))
        mock_context.read_file_state = mock_read_state

        result = await notebook_edit_tool.validate_input(
            {
                "notebookPath": temp_notebook,
                "cellId": "cell-1",
                "newSource": "print('updated')",
                "editMode": "replace",
            },
            mock_context,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_call_replace_cell(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        result = await notebook_edit_tool.call(
            {
                "notebookPath": temp_notebook,
                "cellId": "cell-1",
                "newSource": "print('updated cell')\n",
                "editMode": "replace",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data["success"] is True
        assert result.data["cell_id"] == "cell-1"
        assert result.data["edit_mode"] == "replace"

    @pytest.mark.asyncio
    async def test_call_insert_cell(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        result = await notebook_edit_tool.call(
            {
                "notebookPath": temp_notebook,
                "cellId": "cell-1",
                "newSource": "# New markdown cell\n",
                "cellType": "markdown",
                "editMode": "insert",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data["success"] is True
        assert result.data["edit_mode"] == "insert"

    @pytest.mark.asyncio
    async def test_call_delete_cell(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock, temp_notebook: str
    ) -> None:
        result = await notebook_edit_tool.call(
            {
                "notebookPath": temp_notebook,
                "cellId": "cell-1",
                "editMode": "delete",
            },
            mock_context,
            AsyncMock(),
            None,
        )
        assert result.data["success"] is True
        assert result.data["edit_mode"] == "delete"

    @pytest.mark.asyncio
    async def test_call_error_invalid_json(
        self, notebook_edit_tool: NotebookEditTool, mock_context: MagicMock
    ) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ipynb", delete=False, mode="w") as f:
            f.write("invalid json {{{")
            invalid_file = f.name

        try:
            result = await notebook_edit_tool.call(
                {
                    "notebookPath": invalid_file,
                    "newSource": "print('test')",
                    "editMode": "replace",
                },
                mock_context,
                AsyncMock(),
                None,
            )
            assert result.data["success"] is False
            assert "error" in result.data
        finally:
            import os
            os.unlink(invalid_file)

    def test_map_tool_result_replace(
        self, notebook_edit_tool: NotebookEditTool
    ) -> None:
        content = {
            "success": True,
            "notebookPath": "/path/to/notebook.ipynb",
            "cellId": "cell-1",
            "editMode": "replace",
            "newSource": "print('updated')",
        }
        result = notebook_edit_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-nb"
        )
        assert result["tool_use_id"] == "tool-use-nb"
        assert result["type"] == "tool_result"

    def test_map_tool_result_insert(
        self, notebook_edit_tool: NotebookEditTool
    ) -> None:
        content = {
            "success": True,
            "notebookPath": "/path/to/notebook.ipynb",
            "cellId": "new-cell-id",
            "editMode": "insert",
        }
        result = notebook_edit_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-nb2"
        )
        assert result["tool_use_id"] == "tool-use-nb2"
        assert "insert" in result["content"].lower()

    def test_map_tool_result_delete(
        self, notebook_edit_tool: NotebookEditTool
    ) -> None:
        content = {
            "success": True,
            "notebookPath": "/path/to/notebook.ipynb",
            "cellId": "cell-1",
            "editMode": "delete",
        }
        result = notebook_edit_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-nb3"
        )
        assert result["tool_use_id"] == "tool-use-nb3"
        assert "delete" in result["content"].lower()

    def test_map_tool_result_error(
        self, notebook_edit_tool: NotebookEditTool
    ) -> None:
        content = {
            "success": False,
            "error": "Cell not found",
        }
        result = notebook_edit_tool.map_tool_result_to_tool_result_block_param(
            content, "tool-use-nb4"
        )
        assert result["tool_use_id"] == "tool-use-nb4"
        assert "error" in result["content"].lower() or "not found" in result["content"].lower()
