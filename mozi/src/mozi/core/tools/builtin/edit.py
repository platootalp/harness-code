"""EditFileTool - Edit file contents using string replacement."""

import re
import time
from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.security import path_whitelist_validation


class EditFileTool(Tool):
    """Tool for editing file contents using string replacement.

    Provides safe file editing with:
    - String replacement logic
    - Path whitelist validation
    - Permission level enforcement
    """

    def __init__(self) -> None:
        """Initialize the EditFileTool."""
        super().__init__(
            name="edit",
            description="Edit file contents using string replacement",
            version="1.0.0",
        )

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for edit tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "String to replace",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement string",
                    },
                    "use_regex": {
                        "type": "boolean",
                        "description": "Use regex matching for old_string",
                        "default": False,
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        }

    async def execute(self, context: ToolContext) -> ToolResult:
        """Edit a file using string replacement.

        Args:
            context: Execution context with file path and replacement info.

        Returns:
            ToolResult with success status or error.
        """
        start_time = time.time()
        file_path = context.parameters.get("path", "")
        old_string = context.parameters.get("old_string", "")
        new_string = context.parameters.get("new_string", "")
        use_regex = context.parameters.get("use_regex", False)

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
                error="Insufficient permission level for file edit (requires level 2)",
                execution_time=time.time() - start_time,
            )

        try:
            # Read current content
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Perform replacement
            if use_regex:
                new_content, count = re.subn(old_string, new_string, content, count=1)
            else:
                if old_string in content:
                    new_content = content.replace(old_string, new_string, 1)
                    count = 1
                else:
                    new_content = content
                    count = 0

            if count == 0:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    error=f"String not found: {old_string}",
                    execution_time=time.time() - start_time,
                )

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                output=f"Replaced {count} occurrence(s) in {file_path}",
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
