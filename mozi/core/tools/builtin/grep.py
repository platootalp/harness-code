"""GrepTool - Search file contents using patterns."""

import re
import time
from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.security import path_whitelist_validation


class GrepTool(Tool):
    """Tool for searching file contents using patterns.

    Provides grep-like functionality with:
    - Regex pattern support
    - Path whitelist validation
    - Permission level enforcement
    """

    def __init__(self) -> None:
        """Initialize the GrepTool."""
        super().__init__(
            name="grep",
            description="Search for patterns in files",
            version="1.0.0",
        )

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for grep tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Path to file or directory to search",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively in directories",
                        "default": False,
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Case sensitive matching",
                        "default": True,
                    },
                    "line_numbers": {
                        "type": "boolean",
                        "description": "Include line numbers in output",
                        "default": True,
                    },
                },
                "required": ["pattern", "path"],
            },
        }

    async def execute(self, context: ToolContext) -> ToolResult:
        """Search for a pattern in files.

        Args:
            context: Execution context with pattern and path.

        Returns:
            ToolResult with search matches or error.
        """
        start_time = time.time()
        pattern = context.parameters.get("pattern", "")
        file_path = context.parameters.get("path", "")
        recursive = context.parameters.get("recursive", False)
        case_sensitive = context.parameters.get("case_sensitive", True)
        line_numbers = context.parameters.get("line_numbers", True)

        # Validate path
        is_valid, error_msg = path_whitelist_validation(
            file_path, context.allowed_paths
        )
        if not is_valid:
            return ToolResult(
                status=ToolStatus.DENIED,
                error=error_msg,
                execution_time=time.time() - start_time,
            )

        # Check permission level
        if context.permission_level < 1:
            return ToolResult(
                status=ToolStatus.DENIED,
                error="Insufficient permission level for grep (requires level 1)",
                execution_time=time.time() - start_time,
            )

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            matches: list[str] = []
            import os

            if os.path.isfile(file_path):
                file_paths = [file_path]
            elif os.path.isdir(file_path):
                if recursive:
                    file_paths = [
                        os.path.join(root, f)
                        for root, _, files in os.walk(file_path)
                        for f in files
                        if f.endswith(".py")
                    ]
                else:
                    file_paths = [
                        os.path.join(file_path, f)
                        for f in os.listdir(file_path)
                        if os.path.isfile(os.path.join(file_path, f))
                        and f.endswith(".py")
                    ]
            else:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    error=f"Invalid path: {file_path}",
                    execution_time=time.time() - start_time,
                )

            for fp in file_paths:
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                if line_numbers:
                                    matches.append(f"{fp}:{line_num}:{line.rstrip()}")
                                else:
                                    matches.append(f"{fp}:{line.rstrip()}")
                except (PermissionError, OSError):
                    continue

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="\n".join(matches) if matches else "No matches found",
                execution_time=time.time() - start_time,
            )

        except re.error as e:
            return ToolResult(
                status=ToolStatus.FAILURE,
                error=f"Invalid regex pattern: {e}",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time,
            )
