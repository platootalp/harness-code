"""Bash tool - Execute shell commands with security controls."""

import asyncio
import time
from typing import Any

from mozi.core.tools.framework import Tool, ToolContext, ToolResult, ToolStatus
from mozi.core.tools.security import DangerousFunctionDetector


class BashTool(Tool):
    """Tool for executing bash/shell commands.

    This tool provides controlled shell command execution with:
    - Dangerous function detection
    - Path validation
    - Timeout control
    - Permission level enforcement
    """

    def __init__(self) -> None:
        """Initialize the BashTool."""
        super().__init__(
            name="bash",
            description="Execute shell commands in a controlled environment",
            version="1.0.0",
        )
        self._detector = DangerousFunctionDetector()

    @property
    def schema(self) -> dict[str, Any]:
        """Return the JSON schema for bash tool parameters."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        }

    async def execute(self, context: ToolContext) -> ToolResult:
        """Execute a bash command.

        Args:
            context: Execution context with command and parameters.

        Returns:
            ToolResult with command output or error.
        """
        start_time = time.time()
        command = context.parameters.get("command", "")
        timeout = context.parameters.get("timeout", 30)

        # Validate permission level
        if context.permission_level < 3:
            return ToolResult(
                status=ToolStatus.DENIED,
                error="Insufficient permission level for bash execution (requires level 3)",
                execution_time=time.time() - start_time,
            )

        # Detect dangerous functions
        violations = self._detector.detect(command)
        if violations:
            violation_msgs = [v.message for v in violations]
            return ToolResult(
                status=ToolStatus.DENIED,
                error=f"Command blocked due to security violations: {violation_msgs}",
                execution_time=time.time() - start_time,
            )

        # Check for dangerous command patterns
        dangerous_patterns = [
            "rm -rf",
            "dd if=",
            ":(){:|:&};:",
            "curl | sh",
            "wget | sh",
        ]
        for pattern in dangerous_patterns:
            if pattern in command:
                return ToolResult(
                    status=ToolStatus.DENIED,
                    error=f"Command contains dangerous pattern: {pattern}",
                    execution_time=time.time() - start_time,
                )

        # Execute command
        try:
            cwd = context.working_directory if context.working_directory else None
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=context.env_vars,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(
                    status=ToolStatus.TIMEOUT,
                    error=f"Command timed out after {timeout} seconds",
                    execution_time=time.time() - start_time,
                )

            if proc.returncode == 0:
                return ToolResult(
                    status=ToolStatus.SUCCESS,
                    output=stdout.decode("utf-8", errors="replace"),
                    execution_time=time.time() - start_time,
                )
            else:
                return ToolResult(
                    status=ToolStatus.FAILURE,
                    output=stdout.decode("utf-8", errors="replace"),
                    error=stderr.decode("utf-8", errors="replace"),
                    execution_time=time.time() - start_time,
                )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time,
            )
