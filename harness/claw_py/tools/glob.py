"""
GlobTool - Find files matching a glob pattern.

Migrated from src/tools/GlobTool/GlobTool.ts.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name
# =============================================================================

GLOB_TOOL_NAME = "Glob"


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class GlobToolOutput:
    """Output from the GlobTool."""

    duration_ms: float
    num_files: int
    filenames: list[str]
    truncated: bool


# =============================================================================
# GlobTool
# =============================================================================


class GlobTool(BaseTool):
    """Tool for finding files matching a glob pattern.

    This tool searches the filesystem for files matching a given pattern.
    It is read-only and concurrency-safe.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "find files by name pattern or wildcard"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    @property
    def name(self) -> str:
        return GLOB_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "The directory to search in. If not specified, the current "
                        "working directory will be used. IMPORTANT: Omit this field "
                        "to use the default directory. DO NOT enter 'undefined' or "
                        "'null' - simply omit it for the default behavior. "
                        "Must be a valid directory path if provided."
                    ),
                },
            },
            "required": ["pattern"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return True

    def is_read_only(self, input: Any) -> bool:
        return True

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        return {"is_search": True, "is_read": False}

    def get_path(self, input: Any) -> str | None:
        path = input.get("path")
        if path:
            return os.path.abspath(path)
        return os.getcwd()

    def to_auto_classifier_input(self, input: Any) -> str:
        return input.get("pattern", "")

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        pattern = input.get("pattern")
        if not pattern:
            return (False, "pattern is required", 400)

        path = input.get("path")
        if path:
            abs_path = os.path.abspath(path)
            if not os.path.isdir(abs_path):
                return (False, f"Path is not a directory: {path}", 400)

        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[GlobToolOutput]:
        """Execute the glob tool.

        Args:
            args: Tool input with pattern and optional path.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with glob search results.
        """
        pattern = args.get("pattern", "")
        search_path = args.get("path")

        start_time = time.perf_counter()

        # Determine the search directory
        base_dir = os.path.abspath(search_path) if search_path else os.getcwd()

        # Handle glob limits from context
        max_results = 100
        limits = context.glob_limits if context.glob_limits else {}
        if limits:
            max_results = limits.get("max_results", max_results)

        # Perform glob search
        matched_files: list[str] = []
        try:
            import fnmatch

            # Translate ** globstar pattern to * for fnmatch compatibility
            # ** in a glob pattern means "match any number of directories"
            # fnmatch doesn't support **, so we translate it
            fnmatch_pattern = pattern.replace("**/", "*").replace("**", "*")

            for root, dirs, files in os.walk(base_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in files:
                    if fnmatch.fnmatch(filename, fnmatch_pattern):
                        full_path = os.path.join(root, filename)
                        matched_files.append(full_path)

                    if len(matched_files) >= max_results:
                        break

                if len(matched_files) >= max_results:
                    break

        except OSError:
            pass

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Sort results
        matched_files.sort()

        truncated = len(matched_files) >= max_results
        if truncated:
            matched_files = matched_files[:max_results]

        output = GlobToolOutput(
            duration_ms=round(duration_ms, 2),
            num_files=len(matched_files),
            filenames=matched_files,
            truncated=truncated,
        )

        return ToolResult(data=output)

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        return (
            "A tool for finding files by glob pattern. "
            "Use this to search for files matching a pattern like '*.py' or '**/*.ts'."
        )

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The Glob tool finds files matching a glob pattern. "
            "Examples: '*.py' finds all Python files, '**/*.ts' finds all TypeScript files recursively. "
            "Pattern syntax: * matches anything, ** matches paths, ? matches single char, [abc] matches char sets."
        )
