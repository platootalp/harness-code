"""
NotebookEditTool - Edit Jupyter notebook cells.

Migrated from src/tools/NotebookEditTool/NotebookEditTool.ts.
"""

from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)

if TYPE_CHECKING:
    pass


NOTEBOOK_EDIT_TOOL_NAME = "NotebookEdit"


def parse_cell_id(cell_id: str) -> int | None:
    """Parse a cell ID in 'cell-N' format."""
    match = re.match(r"^cell-(\d+)$", cell_id)
    if match:
        return int(match.group(1)) - 1
    return None


def _read_file_state_get(context: ToolUseContext, path: str) -> Any | None:
    """Get read timestamp from context read_file_state."""
    read_file_state = getattr(context, "read_file_state", None)
    if read_file_state is None:
        return None
    get_method = getattr(read_file_state, "get", None)
    if get_method:
        return get_method(path)
    if isinstance(read_file_state, dict):
        return read_file_state.get(path)
    return None


def _safe_parse_json(content: str) -> Any | None:
    """Parse JSON safely, returning None on error."""
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None


def _read_text_file(path: str) -> str | None:
    """Read a text file safely."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _write_text_file(path: str, content: str) -> bool:
    """Write text to a file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except OSError:
        return False


def _get_file_modification_time(path: str) -> int:
    """Get file modification time in seconds."""
    try:
        return int(os.stat(path).st_mtime)
    except OSError:
        return 0


class NotebookEditTool(BaseTool):
    """Tool for editing Jupyter notebook cells."""

    aliases: list[str] | None = None
    search_hint: str | None = "edit Jupyter notebook cells (.ipynb)"
    should_defer: bool = True
    always_load: bool = False
    max_result_size_chars: int = 100_000
    strict: bool = True

    @property
    def name(self) -> str:
        return NOTEBOOK_EDIT_TOOL_NAME

    @property
    def description_text(self) -> str:
        return (
            "A tool for editing Jupyter notebook (.ipynb) cells. "
            "Supports replace, insert, and delete operations."
        )

    @property
    def prompt_text(self) -> str:
        return (
            "Use this tool to edit Jupyter notebook cells. "
            "Required: notebookPath, newSource. "
            "Optional: cellId, cellType, editMode."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "notebook_path": {
                    "type": "string",
                    "description": "The absolute path to the Jupyter notebook file",
                },
                "cell_id": {
                    "type": "string",
                    "description": "The ID of the cell to edit",
                },
                "new_source": {
                    "type": "string",
                    "description": "The new source for the cell",
                },
                "cell_type": {
                    "type": "string",
                    "enum": ["code", "markdown"],
                    "description": "The type of cell (code or markdown)",
                },
                "edit_mode": {
                    "type": "string",
                    "enum": ["replace", "insert", "delete"],
                    "description": "The edit mode (replace/insert/delete)",
                },
            },
            "required": ["notebook_path", "new_source"],
        }

    @property
    def output_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "new_source": {"type": "string"},
                "cell_id": {"type": "string"},
                "cell_type": {"type": "string"},
                "language": {"type": "string"},
                "edit_mode": {"type": "string"},
                "error": {"type": "string"},
                "notebook_path": {"type": "string"},
                "original_file": {"type": "string"},
                "updated_file": {"type": "string"},
            },
        }

    def user_facing_name(self, input: Any | None = None) -> str:
        return "Edit Notebook"

    def to_auto_classifier_input(self, input: Any) -> str:
        path = input.get("notebook_path", input.get("notebookPath", ""))
        edit_mode = input.get("edit_mode", input.get("editMode", "replace"))
        new_source = input.get("new_source", input.get("newSource", ""))
        return f"{path} {edit_mode}: {new_source}"

    def get_path(self, input: Any) -> str | None:
        path = input.get("notebook_path", input.get("notebookPath", ""))
        return path if path else None

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the notebook edit tool input."""
        notebook_path = input.get("notebook_path") or input.get("notebookPath", "")
        cell_id = input.get("cell_id") or input.get("cellId")
        cell_type = input.get("cell_type") or input.get("cellType")
        edit_mode = input.get("edit_mode") or input.get("editMode", "replace")

        if not notebook_path:
            return (False, "notebook_path is required", 3)

        ext = os.path.splitext(notebook_path)[1]
        if ext != ".ipynb":
            return (
                False,
                "File must be a Jupyter notebook (.ipynb file).",
                2,
            )

        if edit_mode not in ("replace", "insert", "delete"):
            return (False, "Edit mode must be replace, insert, or delete.", 4)

        if edit_mode == "insert" and not cell_type:
            return (False, "Cell type is required when using edit_mode=insert.", 5)

        if notebook_path.startswith("\\\\") or notebook_path.startswith("//"):
            return True

        read_timestamp = _read_file_state_get(context, notebook_path)
        if read_timestamp is None:
            return (
                False,
                "File has not been read yet. Read it first before writing to it.",
                9,
            )

        try:
            current_mtime = _get_file_modification_time(notebook_path)
            read_ts_value = (
                read_timestamp.timestamp
                if hasattr(read_timestamp, "timestamp")
                else read_timestamp
            )
            if isinstance(read_ts_value, (int, float)) and current_mtime > read_ts_value:
                return (
                    False,
                    "File has been modified since read.",
                    10,
                )
        except OSError:
            pass

        content = _read_text_file(notebook_path)
        if content is None:
            return (False, "Notebook file does not exist.", 1)

        notebook = _safe_parse_json(content)
        if notebook is None:
            return (False, "Notebook is not valid JSON.", 6)

        cells = notebook.get("cells", []) if isinstance(notebook, dict) else []
        if not cell_id:
            if edit_mode != "insert":
                return (False, "Cell ID must be specified.", 7)
        else:
            cell_index = -1
            for i, cell in enumerate(cells):
                if isinstance(cell, dict) and cell.get("id") == cell_id:
                    cell_index = i
                    break
            if cell_index == -1:
                parsed_index = parse_cell_id(str(cell_id))
                if parsed_index is not None:
                    if not (0 <= parsed_index < len(cells)):
                        return (False, f"Cell index {parsed_index} out of bounds.", 7)
                else:
                    return (False, f'Cell with ID "{cell_id}" not found.', 8)

        return True

    async def call(
        self,
        args: dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[dict[str, Any]]:
        """Execute a notebook edit operation."""
        notebook_path = args.get("notebook_path") or args.get("notebookPath", "")
        cell_id = args.get("cell_id") or args.get("cellId")
        new_source = args.get("new_source") or args.get("newSource", "")
        cell_type = args.get("cell_type") or args.get("cellType")
        edit_mode = args.get("edit_mode") or args.get("editMode", "replace")
        full_path = notebook_path

        try:
            content = _read_text_file(full_path)
            if content is None:
                return ToolResult(
                    data=self._make_error_output(
                        new_source, cell_type or "code", edit_mode,
                        "Notebook file does not exist.", cell_id, full_path,
                    )
                )

            try:
                notebook: dict[str, Any] = json.loads(content)
            except json.JSONDecodeError:
                return ToolResult(
                    data=self._make_error_output(
                        new_source, cell_type or "code", edit_mode,
                        "Notebook is not valid JSON.", cell_id, full_path,
                        original_content=content,
                    )
                )

            cells = notebook.get("cells", [])

            cell_index: int
            if not cell_id:
                cell_index = 0
            else:
                cell_index = -1
                for i, cell in enumerate(cells):
                    if isinstance(cell, dict) and cell.get("id") == cell_id:
                        cell_index = i
                        break
                if cell_index == -1:
                    parsed_index = parse_cell_id(str(cell_id))
                    cell_index = parsed_index if parsed_index is not None else -1
                if edit_mode == "insert" and cell_index >= 0:
                    cell_index += 1

            resolved_edit_mode = edit_mode
            if edit_mode == "replace" and cell_index >= len(cells):
                resolved_edit_mode = "insert"
                if not cell_type:
                    cell_type = "code"

            language = "python"
            if isinstance(notebook, dict):
                metadata = notebook.get("metadata", {})
                if isinstance(metadata, dict):
                    lang_info = metadata.get("language_info", {})
                    if isinstance(lang_info, dict):
                        language = lang_info.get("name", "python")

            nbformat = notebook.get("nbformat", 4)
            nbformat_minor = notebook.get("nbformat_minor", 4)
            supports_cell_ids = nbformat > 4 or (nbformat == 4 and nbformat_minor >= 5)

            new_cell_id: str | None = None

            if resolved_edit_mode == "delete":
                if 0 <= cell_index < len(cells):
                    cells.pop(cell_index)
            elif resolved_edit_mode == "insert":
                new_cell_id = (
                    f"{int(10**12 * __import__('random').random()):x}"
                    if supports_cell_ids else None
                )
                new_cell: dict[str, Any] = {
                    "id": new_cell_id,
                    "source": new_source,
                    "metadata": {},
                }
                if cell_type == "markdown":
                    new_cell["cell_type"] = "markdown"
                else:
                    new_cell["cell_type"] = "code"
                    new_cell["execution_count"] = None
                    new_cell["outputs"] = []
                cells.insert(cell_index, new_cell)
            else:
                if 0 <= cell_index < len(cells):
                    target_cell = cells[cell_index]
                    if isinstance(target_cell, dict):
                        target_cell["source"] = new_source
                        if target_cell.get("cell_type") == "code":
                            target_cell["execution_count"] = None
                            target_cell["outputs"] = []
                        if cell_type and cell_type != target_cell.get("cell_type"):
                            target_cell["cell_type"] = cell_type
                        if supports_cell_ids and cell_id:
                            new_cell_id = cell_id
                else:
                    return ToolResult(
                        data=self._make_error_output(
                            new_source, cell_type or "code", resolved_edit_mode,
                            f"Cell index {cell_index} out of bounds.",
                            cell_id, full_path, original_content=content,
                        )
                    )

            updated_content = json.dumps(notebook, indent=1) + "\n"
            if not _write_text_file(full_path, updated_content):
                return ToolResult(
                    data=self._make_error_output(
                        new_source, cell_type or "code", resolved_edit_mode,
                        "Failed to write notebook file.", cell_id, full_path,
                        original_content=content,
                    )
                )

            read_file_state = getattr(context, "read_file_state", None)
            if read_file_state is not None:
                post_mtime = _get_file_modification_time(full_path)
                set_method = getattr(read_file_state, "set", None)
                if set_method:
                    set_method(
                        full_path,
                        {
                            "content": updated_content,
                            "timestamp": post_mtime,
                            "offset": None,
                            "limit": None,
                        },
                    )

            return ToolResult(
                data={
                    "new_source": new_source,
                    "cell_type": cell_type or "code",
                    "language": language,
                    "edit_mode": resolved_edit_mode,
                    "cell_id": new_cell_id or cell_id,
                    "error": "",
                    "notebook_path": full_path,
                    "original_file": content,
                    "updated_file": updated_content,
                    "success": True,
                }
            )

        except Exception as e:
            return ToolResult(
                data=self._make_error_output(
                    new_source, cell_type or "code", edit_mode,
                    str(e), cell_id, full_path,
                )
            )

    def _make_error_output(
        self,
        new_source: str,
        cell_type: str,
        edit_mode: str,
        error: str,
        cell_id: str | None,
        notebook_path: str,
        original_content: str = "",
        updated_content: str = "",
    ) -> dict[str, Any]:
        """Create an error output dict."""
        return {
            "new_source": new_source,
            "cell_type": cell_type,
            "language": "python",
            "edit_mode": edit_mode,
            "cell_id": cell_id,
            "error": error,
            "notebook_path": notebook_path,
            "original_file": original_content,
            "updated_file": updated_content,
            "success": False,
        }

    def map_tool_result_to_tool_result_block_param(
        self,
        content: dict[str, Any],
        tool_use_id: str,
    ) -> dict[str, Any]:
        """Map notebook edit tool result to tool result block param."""
        error = content.get("error", "")
        edit_mode = content.get("edit_mode", content.get("editMode", ""))
        cell_id = content.get("cell_id", content.get("cellId", ""))
        content.get("new_source", content.get("newSource", ""))

        if error:
            return {
                "tool_use_id": tool_use_id,
                "type": "tool_result",
                "content": error,
                "is_error": True,
            }

        _MODE_MESSAGES = {
            "replace": f"Updated cell {cell_id}",
            "insert": f"Inserted cell {cell_id}",
            "delete": f"Deleted cell {cell_id}",
        }
        msg = _MODE_MESSAGES.get(edit_mode, "No changes made")
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": msg,
        }
