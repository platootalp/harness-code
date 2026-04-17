"""ReadFileTool - Read file contents with path validation."""

import time
from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.security import path_whitelist_validation


class ReadFileTool(Tool):
    """Tool for reading file contents.

    Provides safe file reading with:
    - Path whitelist validation
    - Permission level enforcement
    """

    def __init__(self) -> None:
        """Initialize the ReadFileTool."""
        super().__init__(
            name="read",
            description="Read contents of a file",
            version="1.0.0",
        )

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for read tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line offset to start reading from",
                    },
                },
                "required": ["path"],
            },
        }

    async def execute(self, context: ToolContext) -> ToolResult:
        """Read a file.

        Args:
            context: Execution context with file path.

        Returns:
            ToolResult with file contents or error.
        """
        start_time = time.time()
        file_path = context.parameters.get("path", "")
        limit = context.parameters.get("limit")
        offset = context.parameters.get("offset", 0)

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
                error="Insufficient permission level for file read (requires level 1)",
                execution_time=time.time() - start_time,
            )

        try:
            with open(file_path, encoding="utf-8") as f:
                if offset > 0:
                    # Seek to offset
                    for _ in range(offset):
                        f.readline()

                content = f.read()

                if limit:
                    lines = content.splitlines()
                    content = "\n".join(lines[:limit])

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=content,
                execution_time=time.time() - start_time,
            )

        except FileNotFoundError:
            return ToolResult(
                status=ToolStatus.FAILURE,
                error=f"File not found: {file_path}",
                execution_time=time.time() - start_time,
            )
        except PermissionError:
            return ToolResult(
                status=ToolStatus.DENIED,
                error=f"Permission denied: {file_path}",
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time,
            )
