"""
FileEditTool - Edit file contents in place.

Migrated from src/tools/FileEditTool/FileEditTool.ts.
"""

from __future__ import annotations

import contextlib
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
from ..utils.file import (
    FILE_NOT_FOUND_CWD_NOTE,
    expand_path,
    get_file_modification_time,
    suggest_path_under_cwd,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name & Constants
# =============================================================================

FILE_EDIT_TOOL_NAME = "Edit"
FILE_UNEXPECTEDED_MODIFIED_ERROR = "File was unexpectedly modified since it was read."

# Maximum file size (1 GiB)
MAX_EDIT_FILE_SIZE = 1024 * 1024 * 1024


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
class FileEditToolOutput:
    """Output from the FileEditTool."""

    file_path: str
    old_string: str
    new_string: str
    new_content: str
    changed: bool
    structured_patch: list[Hunk]
    git_diff: str | None = None


# =============================================================================
# FileEditTool
# =============================================================================


class FileEditTool(BaseTool):
    """Tool for editing files in place.

    Replaces old_string with new_string in a file. Validates that old_string
    exists exactly as specified, and that the file hasn't been modified
    since it was read.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "modify file contents in place"
    max_result_size_chars: int = 100_000
    strict: bool = True
    should_defer: bool = False
    always_load: bool = False

    @property
    def name(self) -> str:
        return FILE_EDIT_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": (
                        "The exact string to find in the file. "
                        "Must match exactly including whitespace and newlines."
                    ),
                },
                "new_string": {
                    "type": "string",
                    "description": (
                        "The string to replace old_string with. "
                        "Must include the replacement text."
                    ),
                },
                "replace_all": {
                    "type": "boolean",
                    "description": (
                        "Replace all occurrences of old_string. "
                        "Defaults to False (first occurrence only)."
                    ),
                },
            },
            "required": ["file_path", "old_string", "new_string"],
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
        file_path = input.get("file_path", "")
        old_str = input.get("old_string", "")
        return f"{file_path}: {old_str[:100]}"

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        file_path = input.get("file_path")
        old_string = input.get("old_string")
        new_string = input.get("new_string")

        if not file_path:
            return (False, "file_path is required", 400)
        if old_string is None:
            return (False, "old_string is required", 400)
        if new_string is None:
            return (False, "new_string is required", 400)

        abs_path = expand_path(file_path)

        # Check file exists
        if not os.path.isfile(abs_path):
            similar = suggest_path_under_cwd(abs_path)
            note = f" {FILE_NOT_FOUND_CWD_NOTE} {os.getcwd()}" if similar else ""
            return (False, f"File not found: {file_path}{note}", 404)

        # Check file size
        try:
            size = os.path.getsize(abs_path)
            if size > MAX_EDIT_FILE_SIZE:
                return (False, f"File too large for editing: {size} bytes", 413)
        except OSError:
            pass

        # Check old_string exists in file
        try:
            with open(abs_path, encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(abs_path, encoding="latin-1") as f:
                    content = f.read()
            except OSError as e:
                return (False, f"Cannot read file: {e}", 400)

        if old_string not in content:
            return (False, f"old_string not found in file: {old_string[:100]}...", 400)

        # Check for multiple occurrences when replace_all is not set
        replace_all = input.get("replace_all", False)
        if not replace_all:
            count = content.count(old_string)
            if count > 1:
                return (
                    False,
                    f"old_string appears {count} times. Use replace_all=true to replace all occurrences.",
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
    ) -> ToolResult[FileEditToolOutput]:
        """Execute the file edit tool.

        Args:
            args: Tool input with file_path, old_string, new_string.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with edit result.
        """
        file_path = args.get("file_path", "")
        old_string = args.get("old_string", "")
        new_string = args.get("new_string", "")
        replace_all = args.get("replace_all", False)

        abs_path = expand_path(file_path)

        # Read current content
        encoding = "utf-8"
        try:
            with open(abs_path, encoding="utf-8") as f:
                old_content = f.read()
        except UnicodeDecodeError:
            encoding = "latin-1"
            with open(abs_path, encoding=encoding) as f:
                old_content = f.read()

        # Check file wasn't modified since validation
        with contextlib.suppress(OSError):
            get_file_modification_time(abs_path)

        # Perform the replacement
        if replace_all:
            new_content = old_content.replace(old_string, new_string)
        else:
            new_content = old_content.replace(old_string, new_string, 1)

        changed = old_content != new_content

        # Build structured patch
        patch = self._build_patch(old_content, new_content, old_string, new_string)

        # Generate git-style diff
        git_diff = self._generate_git_diff(old_content, new_content, file_path)

        # Write the file if changed
        if changed:
            try:
                with open(abs_path, "w", encoding=encoding, newline="") as f:
                    f.write(new_content)
            except OSError:
                return ToolResult(
                    data=FileEditToolOutput(
                        file_path=abs_path,
                        old_string=old_string,
                        new_string=new_string,
                        new_content="",
                        changed=False,
                        structured_patch=[],
                        git_diff=None,
                    )
                )

        output = FileEditToolOutput(
            file_path=abs_path,
            old_string=old_string,
            new_string=new_string,
            new_content=new_content,
            changed=changed,
            structured_patch=patch,
            git_diff=git_diff,
        )

        return ToolResult(data=output)

    def _build_patch(
        self,
        old_content: str,
        new_content: str,
        old_string: str,
        new_string: str,
    ) -> list[Hunk]:
        """Build a structured patch for the edit."""
        hunks: list[Hunk] = []

        # Find the position of old_string in old_content
        pos = old_content.find(old_string)
        if pos == -1:
            return hunks

        # Count lines before the match
        lines_before = old_content[:pos].count("\n")

        old_lines_list = old_string.split("\n")
        new_lines_list = new_string.split("\n")

        hunk = Hunk(
            old_start=lines_before + 1,
            old_lines=len(old_lines_list),
            new_start=lines_before + 1,
            new_lines=len(new_lines_list),
            lines=[f"- {old_string}", f"+ {new_string}"],
        )
        hunks.append(hunk)

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
        return "A tool for editing files in place by replacing text."

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The Edit tool modifies files in place. "
            "Provide the exact old_string to find and the new_string to replace it with. "
            "Use replace_all=true to replace all occurrences. "
            "The old_string must match exactly including whitespace and newlines."
        )
