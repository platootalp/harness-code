"""
GrepTool - Search file contents using regular expressions.

Migrated from src/tools/GrepTool/GrepTool.ts.
"""

from __future__ import annotations

import os
import re
import subprocess
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

GREP_TOOL_NAME = "Grep"

# Version control system directories to exclude from searches
VCS_DIRECTORIES_TO_EXCLUDE = frozenset([
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    ".jj",
])

# Default limit for search results
DEFAULT_HEAD_LIMIT = 250


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class GrepToolOutput:
    """Output from the GrepTool."""

    duration_ms: float
    matches: list[str] | int
    num_matches: int
    truncated: bool
    output_mode: str


# =============================================================================
# GrepTool
# =============================================================================


class GrepTool(BaseTool):
    """Tool for searching file contents using regular expressions.

    This tool uses ripgrep (rg) under the hood for efficient searching.
    It is read-only and concurrency-safe.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "search for text patterns in files"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    @property
    def name(self) -> str:
        return GREP_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regular expression pattern to search for in file contents",
                },
                "path": {
                    "type": "string",
                    "description": (
                        "File or directory to search in (rg PATH). "
                        "Defaults to current working directory."
                    ),
                },
                "glob": {
                    "type": "string",
                    "description": (
                        'Glob pattern to filter files (e.g. "*.js", "*.{ts,tsx}") '
                        "- maps to rg --glob"
                    ),
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": (
                        'Output mode: "content" shows matching lines, '
                        '"files_with_matches" shows file paths, '
                        '"count" shows match counts. '
                        'Defaults to "files_with_matches".'
                    ),
                },
                "-B": {
                    "type": "integer",
                    "description": (
                        "Number of lines to show before each match (rg -B). "
                        "Requires output_mode: 'content'."
                    ),
                },
                "-A": {
                    "type": "integer",
                    "description": (
                        "Number of lines to show after each match (rg -A). "
                        "Requires output_mode: 'content'."
                    ),
                },
                "-C": {
                    "type": "integer",
                    "description": "Number of lines of context (rg -C).",
                },
                "context": {
                    "type": "integer",
                    "description": (
                        "Number of lines to show before and after each match (rg -C)."
                    ),
                },
                "-n": {
                    "type": "boolean",
                    "description": (
                        "Show line numbers in output. "
                        "Requires output_mode: 'content'. Defaults to true."
                    ),
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search (rg -i).",
                },
                "type": {
                    "type": "string",
                    "description": (
                        "File type to search (rg --type). "
                        "Common types: js, py, rust, go, java, etc."
                    ),
                },
                "head_limit": {
                    "type": "integer",
                    "description": (
                        "Limit output to first N lines/entries. "
                        "Works across all output modes. "
                        "Defaults to 250 when unspecified."
                    ),
                },
                "offset": {
                    "type": "integer",
                    "description": (
                        "Skip first N lines/entries before applying head_limit. "
                        "Defaults to 0."
                    ),
                },
                "multiline": {
                    "type": "boolean",
                    "description": (
                        "Enable multiline mode where . matches newlines. Default: false."
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

        # Try to compile as regex to validate
        flags = 0
        if input.get("-i"):
            flags |= re.IGNORECASE
        if input.get("multiline"):
            flags |= re.MULTILINE

        try:
            re.compile(pattern)
        except re.error as e:
            return (False, f"Invalid regex pattern: {e}", 400)

        return True

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[GrepToolOutput]:
        """Execute the grep tool.

        Args:
            args: Tool input with pattern and options.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with grep search results.
        """
        pattern = args.get("pattern", "")
        path = args.get("path") or os.getcwd()
        glob = args.get("glob")
        output_mode = args.get("output_mode", "files_with_matches")
        head_limit = args.get("head_limit", DEFAULT_HEAD_LIMIT)
        offset = args.get("offset", 0)

        start_time = time.perf_counter()

        # Build ripgrep command
        rg_args = ["rg", "--json"]

        # Exclude VCS directories
        for vcs_dir in VCS_DIRECTORIES_TO_EXCLUDE:
            rg_args.extend(["--glob", f"!{vcs_dir}/**"])

        # Add glob filter
        if glob:
            rg_args.extend(["--glob", glob])

        # Output mode
        if output_mode == "content":
            rg_args.append("--text")
            if args.get("-n", True):
                rg_args.append("--line-number")
        elif output_mode == "count":
            rg_args.append("--count")
        # files_with_matches is default in JSON mode

        # Context lines
        if args.get("-B"):
            rg_args.extend(["--before-context", str(args["-B"])])
        if args.get("-A"):
            rg_args.extend(["--after-context", str(args["-A"])])
        context_val = args.get("-C") or args.get("context")
        if context_val:
            rg_args.extend(["--context", str(context_val)])

        # Flags
        if args.get("-i"):
            rg_args.append("--smart-case")
        if args.get("multiline"):
            rg_args.append("--multiline")

        # Type filter
        if args.get("type"):
            rg_args.extend(["--type", args["type"]])

        # Pattern and path
        rg_args.append(pattern)
        rg_args.append(path)

        try:
            result = subprocess.run(
                rg_args,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.TimeoutExpired, OSError):
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                data=GrepToolOutput(
                    duration_ms=round(duration_ms, 2),
                    matches=[],
                    num_matches=0,
                    truncated=False,
                    output_mode=output_mode,
                )
            )

        # Parse JSON output from ripgrep
        matches: list[str] = []
        num_matches = 0

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                import json

                entry = json.loads(line)
                if entry.get("type") == "match":
                    num_matches += 1
                    if output_mode == "content":
                        match_data = entry.get("data", {})
                        lines_data = match_data.get("lines", {}).get("text", "")
                        matches.append(lines_data.rstrip())
                    elif output_mode == "files_with_matches":
                        match_data = entry.get("data", {})
                        path_info = match_data.get("path", {})
                        if isinstance(path_info, dict):
                            path_str = path_info.get("text", "")
                        else:
                            path_str = str(path_info)
                        if path_str and path_str not in matches:
                            matches.append(path_str)
                    elif output_mode == "count":
                        match_data = entry.get("data", {})
                        path_info = match_data.get("path", {})
                        if isinstance(path_info, dict):
                            path_str = path_info.get("text", "")
                        else:
                            path_str = str(path_info)
                        count = match_data.get("line_number", 0)
                        matches.append(f"{path_str}:{count}")
            except (json.JSONDecodeError, KeyError):
                continue

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Apply offset and head_limit
        if offset > 0:
            matches = matches[offset:]
        truncated = False
        if head_limit > 0 and len(matches) > head_limit:
            matches = matches[:head_limit]
            truncated = True

        return ToolResult(
            data=GrepToolOutput(
                duration_ms=round(duration_ms, 2),
                matches=matches,
                num_matches=num_matches,
                truncated=truncated,
                output_mode=output_mode,
            )
        )

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        return (
            "A tool for searching file contents using regular expressions. "
            "Use this to find text matching a pattern across files."
        )

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The Grep tool searches file contents using regular expressions. "
            "Supports case-insensitive search (-i), line numbers (-n), "
            "context lines (-C), and file type filters (--type). "
            "Use output_mode 'content' to see matching lines with context, "
            "'files_with_matches' to see only file names, "
            "or 'count' to see match counts per file."
        )
