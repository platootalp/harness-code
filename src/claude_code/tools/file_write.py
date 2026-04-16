"""
FileWriteTool - Write content to files.

Migrated from src/tools/FileWriteTool/FileWriteTool.ts.
"""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)
from ..utils.file import expand_path

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

FILE_WRITE_TOOL_NAME = "Write"


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class Hunk:
    """A single diff hunk."""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: list[str]


@dataclass
class FileWriteToolOutput:
    """Output from the FileWriteTool."""

    type: str  # "create" or "update"
    file_path: str
    content: str
    structured_patch: list[Hunk]
    original_file: str | None
    git_diff: str | None = None


# =============================================================================
# FileWriteTool
# =============================================================================


class FileWriteTool(BaseTool):
    """Tool for writing content to files.

    Creates new files or overwrites existing files with the provided content.
    Computes git-style diffs and structured patches for the changes.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "create or overwrite files"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    def __init__(self) -> None:
        self.strict = True

    @property
    def name(self) -> str:
        return FILE_WRITE_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "The absolute path to the file to write "
                        "(must be absolute, not relative)"
                    ),
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return False

    def is_read_only(self, input: Any) -> bool:
        return False

    def is_destructive(self, input: Any) -> bool:
        return True

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        return {"is_search": False, "is_read": False}

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
        content = input.get("content")

        if not file_path:
            return (False, "file_path is required", 400)

        if content is None:
            return (False, "content is required", 400)

        abs_path = expand_path(file_path)

        # Ensure parent directory exists
        parent = os.path.dirname(abs_path)
        if parent and not os.path.isdir(parent):
            return (
                False,
                f"Parent directory does not exist: {parent}",
                400,
            )

        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[FileWriteToolOutput]:
        """Execute the file write tool.

        Args:
            args: Tool input with file_path and content.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with write result.
        """
        file_path = args.get("file_path", "")
        content = args.get("content", "")

        abs_path = expand_path(file_path)

        # Check if file exists and read original content
        file_exists = os.path.isfile(abs_path)
        original_content: str | None = None

        if file_exists:
            try:
                with open(abs_path, encoding="utf-8", newline="") as f:
                    original_content = f.read()
            except (UnicodeDecodeError, OSError):
                original_content = None

        # Write the file
        try:
            # Detect line endings from existing file
            line_ending = "\n"
            if original_content is not None and "\r\n" in original_content:
                line_ending = "\r\n"

            # Convert line endings in content to match existing file
            if line_ending == "\r\n":
                content_to_write = content.replace("\r\n", "\n").replace("\n", "\r\n")
            else:
                content_to_write = content.replace("\r\n", "\n")

            with open(abs_path, "w", encoding="utf-8", newline="") as f:
                f.write(content_to_write)
        except OSError:
            output = FileWriteToolOutput(
                type="create" if not file_exists else "update",
                file_path=abs_path,
                content="",
                structured_patch=[],
                original_file=original_content,
                git_diff=None,
            )
            return ToolResult(data=output)

        # Build structured patch (compare after line ending normalization)
        patch: list[Hunk] = []
        git_diff: str | None = None

        if original_content is not None:
            # Normalize line endings for diff comparison
            normalized_old = original_content.replace("\r\n", "\n")
            normalized_new = content.replace("\r\n", "\n")
            if normalized_old != normalized_new:
                patch = self._build_patch(normalized_old, normalized_new)
                git_diff = self._generate_git_diff(
                    normalized_old, normalized_new, file_path
                )

        output = FileWriteToolOutput(
            type="create" if not file_exists else "update",
            file_path=abs_path,
            content=content,
            structured_patch=patch,
            original_file=original_content,
            git_diff=git_diff,
        )

        return ToolResult(data=output)

    def _build_patch(self, old_content: str, new_content: str) -> list[Hunk]:
        """Build a structured patch for the write."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        hunks: list[Hunk] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "insert", "delete"):
                hunks.append(
                    Hunk(
                        old_start=i1 + 1,
                        old_lines=i2 - i1,
                        new_start=j1 + 1,
                        new_lines=j2 - j1,
                        lines=[
                            f"- {old_content}" if tag == "delete" else "",
                            f"+ {new_content}" if tag == "insert" else "",
                        ],
                    )
                )

        return hunks

    def _generate_git_diff(
        self,
        old_content: str,
        new_content: str,
        file_path: str,
    ) -> str | None:
        """Generate a git-style diff string."""
        if old_content == new_content:
            return None

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=file_path,
                tofile=file_path,
                lineterm="",
            )
        )

        return "\n".join(diff)

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        return "Write a file to the local filesystem."

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The Write tool creates or overwrites files with the provided content. "
            "Provide the absolute file_path and the content to write. "
            "Returns the type (create/update), structured diff, and git-style diff."
        )
