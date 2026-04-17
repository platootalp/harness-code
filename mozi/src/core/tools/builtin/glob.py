"""GlobTool - Find files matching glob patterns."""

import os
import time
from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.security import path_whitelist_validation


class GlobTool(Tool):
    """Tool for finding files matching glob patterns.

    Provides glob-like functionality with:
    - Standard glob pattern support
    - Path whitelist validation
    - Permission level enforcement
    """

    def __init__(self) -> None:
        """Initialize the GlobTool."""
        super().__init__(
            name="glob",
            description="Find files matching glob patterns",
            version="1.0.0",
        )

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for glob tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match (e.g., **/*.py)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Base path to search from",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively",
                        "default": True,
                    },
                },
                "required": ["pattern", "path"],
            },
        }

    async def execute(self, context: ToolContext) -> ToolResult:
        """Find files matching a glob pattern.

        Args:
            context: Execution context with pattern and path.

        Returns:
            ToolResult with matching files or error.
        """
        start_time = time.time()
        pattern = context.parameters.get("pattern", "")
        base_path = context.parameters.get("path", "")
        recursive = context.parameters.get("recursive", True)

        # Validate path
        is_valid, error_msg = path_whitelist_validation(
            base_path, context.allowed_paths
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
                error="Insufficient permission level for glob (requires level 1)",
                execution_time=time.time() - start_time,
            )

        try:
            import glob

            # Normalize pattern
            if recursive and not pattern.startswith("**"):
                pattern = "**/" + pattern.lstrip("/")

            full_pattern = os.path.join(base_path, pattern)
            matches = glob.glob(full_pattern, recursive=recursive)

            # Filter to only files
            matches = [m for m in matches if os.path.isfile(m)]

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output="\n".join(matches) if matches else "No matches found",
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time,
            )
