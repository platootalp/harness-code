"""WriteFileTool - Write content to files with atomic write support."""

import os
import tempfile
import time
from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.security import path_whitelist_validation


class WriteFileTool(Tool):
    """Tool for writing content to files.

    Provides safe file writing with:
    - Atomic write (write to temp then rename)
    - Path whitelist validation
    - Permission level enforcement
    """

    def __init__(self) -> None:
        """Initialize the WriteFileTool."""
        super().__init__(
            name="write",
            description="Write content to a file",
            version="1.0.0",
        )

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for write tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "append": {
                        "type": "boolean",
                        "description": "Append to existing file instead of overwriting",
                        "default": False,
                    },
                },
                "required": ["path", "content"],
            },
        }

    async def execute(self, context: ToolContext) -> ToolResult:
        """Write content to a file.

        Args:
            context: Execution context with file path and content.

        Returns:
            ToolResult with success status or error.
        """
        start_time = time.time()
        file_path = context.parameters.get("path", "")
        content = context.parameters.get("content", "")
        append = context.parameters.get("append", False)

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
        if context.permission_level < 2:
            return ToolResult(
                status=ToolStatus.DENIED,
                error="Insufficient permission level for file write (requires level 2)",
                execution_time=time.time() - start_time,
            )

        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            # Atomic write: write to temp file then rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(file_path) or "."
            )
            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    f.write(content)

                mode = os.O_WRONLY | os.O_CREAT
                if append:
                    mode |= os.O_APPEND
                else:
                    mode |= os.O_TRUNC

                os.rename(temp_path, file_path)

            except Exception:
                # Clean up temp file on failure
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Wrote {len(content)} bytes to {file_path}",
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
