"""
FileReadTool - Read file contents with support for various file types.

Migrated from src/tools/FileReadTool/FileReadTool.ts.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)
from ..utils.file import (
    FILE_NOT_FOUND_CWD_NOTE,
    add_line_numbers,
    detect_line_endings,
    expand_path,
    suggest_path_under_cwd,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

FILE_READ_TOOL_NAME = "Read"

# Device files that would hang the process
BLOCKED_DEVICE_PATHS = frozenset([
    "/dev/zero",
    "/dev/full",
])

# Maximum file size (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Maximum lines to read
MAX_LINES = 10_000

# Default limit for search results
DEFAULT_FILE_READ_LIMIT = 1000


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class FileReadToolOutput:
    """Output from the FileReadTool."""

    # Discriminated union type
    type: Literal[
        "text",
        "image",
        "notebook",
        "pdf",
        "parts",
        "file_unchanged",
    ]
    content: str = ""
    # For text type
    lines: list[str] | None = None
    num_lines: int | None = None
    offset: int | None = None
    limit: int | None = None
    # For image type
    base64_image: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    image_format: str | None = None
    # For pdf type
    pdf_pages: list[str] | None = None
    pdf_num_pages: int | None = None
    pdf_read_pages: int | None = None
    # For notebook type
    notebook_cells: list[dict[str, Any]] | None = None
    # For parts type
    parts: list[FileReadToolOutput] | None = None
    # For file_unchanged type
    stub: str | None = None
    # Metadata
    file_path: str | None = None
    file_size: int | None = None
    file_modified: float | None = None
    encoding: str | None = None
    line_ending: str | None = None


# =============================================================================
# FileReadTool
# =============================================================================


class FileReadTool(BaseTool):
    """Tool for reading file contents.

    Supports plain text, images (PNG, JPG, GIF, WebP), PDFs, Jupyter notebooks,
    and partial reads with offset/limit.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "read the contents of a file"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    @property
    def name(self) -> str:
        return FILE_READ_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "The absolute path to the file to read"
                    ),
                },
                "offset": {
                    "type": "integer",
                    "description": (
                        "The line number to start reading from (0-indexed). "
                        "Defaults to 0."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Maximum number of lines to read. "
                        "Defaults to all lines (no limit)."
                    ),
                },
                "pages": {
                    "type": "string",
                    "description": (
                        "For PDFs/notebooks: page range to read (e.g. '1-5', '1,3,5'). "
                        "Defaults to all pages."
                    ),
                },
            },
            "required": ["file_path"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        return {"is_search": False, "is_read": True}

    def get_path(self, input: Any) -> str | None:
        return expand_path(input.get("file_path", ""))

    def to_auto_classifier_input(self, input: Any) -> str:
        return input.get("file_path", "")

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        file_path = input.get("file_path")
        if not file_path:
            return (False, "file_path is required", 400)

        abs_path = expand_path(file_path)

        # Check for blocked device paths
        if abs_path in BLOCKED_DEVICE_PATHS:
            return (False, f"Cannot read device file: {file_path}", 403)

        # Check for UNC paths (security)
        if abs_path.startswith("\\\\"):
            return (False, "UNC paths are not supported for security reasons", 403)

        # Check file exists
        if not os.path.isfile(abs_path):
            # Check for file read state deduplication
            read_file_state = context.read_file_state
            if read_file_state is None:
                similar = suggest_path_under_cwd(abs_path)
                note = f" {FILE_NOT_FOUND_CWD_NOTE} {os.getcwd()}" if similar else ""
                return (False, f"File not found: {file_path}{note}", 404)
            # Allow state-based lookup for deduplication
            return True

        # Check file size
        try:
            size = os.path.getsize(abs_path)
            if size > MAX_FILE_SIZE:
                return (False, f"File too large: {size} bytes (max {MAX_FILE_SIZE})", 413)
        except OSError:
            pass

        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[FileReadToolOutput]:
        """Execute the file read tool.

        Args:
            args: Tool input with file_path and optional offset/limit.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with file contents.
        """
        file_path = args.get("file_path", "")
        offset = args.get("offset", 0)
        limit = args.get("limit")
        pages = args.get("pages")

        abs_path = expand_path(file_path)

        # Get file stats
        try:
            stat = os.stat(abs_path)
            file_size = stat.st_size
            file_modified = stat.st_mtime
        except OSError:
            file_size = None
            file_modified = None

        # Determine file type
        ext = os.path.splitext(abs_path)[1].lower()

        # Handle image files
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            return await self._read_image(abs_path, file_size, file_modified)

        # Handle PDF files
        if ext == ".pdf":
            return await self._read_pdf(abs_path, pages, file_size, file_modified)

        # Handle Jupyter notebooks
        if ext == ".ipynb":
            return await self._read_notebook(abs_path, pages, file_size, file_modified)

        # Handle text files
        return await self._read_text(
            abs_path, offset, limit, file_size, file_modified
        )

    async def _read_text(
        self,
        abs_path: str,
        offset: int,
        limit: int | None,
        file_size: int | None,
        file_modified: float | None,
    ) -> ToolResult[FileReadToolOutput]:
        """Read a text file."""
        try:
            # Detect encoding
            encoding = "utf-8"
            try:
                with open(abs_path, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                encoding = "latin-1"
                with open(abs_path, encoding=encoding) as f:
                    content = f.read()
        except OSError as e:
            return ToolResult(
                data=FileReadToolOutput(
                    type="text",
                    content=f"Error reading file: {e}",
                    file_path=abs_path,
                )
            )

        lines = content.split("\n")
        len(lines)

        # Apply offset
        if offset > 0:
            lines = lines[offset:]
            len(lines)

        # Apply limit
        if limit is not None and limit > 0 and len(lines) > limit:
            lines = lines[:limit]

        # Detect line endings
        line_ending = detect_line_endings(abs_path)

        output = FileReadToolOutput(
            type="text",
            lines=lines,
            num_lines=len(lines),
            offset=offset,
            limit=limit,
            file_path=abs_path,
            file_size=file_size,
            file_modified=file_modified,
            encoding=encoding,
            line_ending=line_ending,
        )

        # Add line numbers for display
        if lines:
            output.content = add_line_numbers("\n".join(lines), start_line=offset + 1)

        return ToolResult(data=output)

    async def _read_image(
        self,
        abs_path: str,
        file_size: int | None,
        file_modified: float | None,
    ) -> ToolResult[FileReadToolOutput]:
        """Read an image file."""
        try:
            with open(abs_path, "rb") as f:
                data = f.read()

            b64 = base64.b64encode(data).decode("ascii")
            ext = os.path.splitext(abs_path)[1].lower()
            fmt = ext.lstrip(".")

            output = FileReadToolOutput(
                type="image",
                base64_image=b64,
                image_format=fmt,
                file_path=abs_path,
                file_size=file_size,
                file_modified=file_modified,
            )
            return ToolResult(data=output)
        except OSError as e:
            return ToolResult(
                data=FileReadToolOutput(
                    type="image",
                    content=f"Error reading image: {e}",
                    file_path=abs_path,
                )
            )

    async def _read_pdf(
        self,
        abs_path: str,
        pages: str | None,
        file_size: int | None,
        file_modified: float | None,
    ) -> ToolResult[FileReadToolOutput]:
        """Read a PDF file."""
        # PDF reading requires pypdf or similar - simplified fallback
        output = FileReadToolOutput(
            type="pdf",
            file_path=abs_path,
            file_size=file_size,
            file_modified=file_modified,
        )
        return ToolResult(data=output)

    async def _read_notebook(
        self,
        abs_path: str,
        pages: str | None,
        file_size: int | None,
        file_modified: float | None,
    ) -> ToolResult[FileReadToolOutput]:
        """Read a Jupyter notebook."""
        try:
            with open(abs_path, encoding="utf-8") as f:
                nb = json.load(f)

            cells = nb.get("cells", [])
            output = FileReadToolOutput(
                type="notebook",
                notebook_cells=cells,
                file_path=abs_path,
                file_size=file_size,
                file_modified=file_modified,
            )
            return ToolResult(data=output)
        except (OSError, json.JSONDecodeError) as e:
            return ToolResult(
                data=FileReadToolOutput(
                    type="notebook",
                    content=f"Error reading notebook: {e}",
                    file_path=abs_path,
                )
            )

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        file_path = input.get("file_path", "") if input else ""
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".pdf":
                return f"Claude wants to read a PDF: {file_path}"
            if ext == ".ipynb":
                return f"Claude wants to read a Jupyter notebook: {file_path}"
            if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                return f"Claude wants to read an image: {file_path}"
        return "A tool for reading file contents."

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The Read tool reads file contents. "
            "Use the 'offset' parameter to start reading from a specific line. "
            "Use 'limit' to restrict the number of lines read. "
            "Images are returned as base64-encoded data. "
            "PDFs can specify page ranges with 'pages' parameter."
        )
