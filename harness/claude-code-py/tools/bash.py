"""
BashTool - Execute bash commands.

Migrated from src/tools/BashTool/BashTool.tsx.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models.tool import (
    BaseTool,
    PermissionAskResult,
    ToolResult,
    ToolUseContext,
    ValidationResult,
)
from ..utils.bash import (
    bash_command_is_safe,
    is_normalized_cd_command,
    is_normalized_git_command,
    split_command,
    strip_safe_wrappers,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Tool Name & Constants
# =============================================================================

BASH_TOOL_NAME = "Bash"

# Progress display constants
PROGRESS_THRESHOLD_MS = 2000

# Assistant blocking budget in ms
ASSISTANT_BLOCKING_BUDGET_MS = 15_000

# Search commands for collapsible display
BASH_SEARCH_COMMANDS = frozenset([
    "find",
    "grep",
    "rg",
    "ag",
    "ack",
    "locate",
    "which",
    "whereis",
])

# Read/view commands for collapsible display
BASH_READ_COMMANDS = frozenset([
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "wc",
    "stat",
    "file",
    "strings",
    "jq",
    "awk",
    "cut",
    "sort",
    "uniq",
    "tr",
])

# Directory listing commands
BASH_LIST_COMMANDS = frozenset(["ls", "tree", "du"])

# Semantic-neutral commands
BASH_SEMANTIC_NEUTRAL_COMMANDS = frozenset([
    "echo",
    "printf",
    "true",
    "false",
    ":",
])

# Silent commands (no stdout on success)
BASH_SILENT_COMMANDS = frozenset([
    "mv",
    "cp",
    "rm",
    "mkdir",
    "rmdir",
    "chmod",
    "chown",
    "chgrp",
    "touch",
    "ln",
    "cd",
    "export",
    "unset",
    "wait",
])


# =============================================================================
# Output Types
# =============================================================================


@dataclass
class BashToolOutput:
    """Output from the BashTool."""

    stdout: str
    stderr: str
    exit_code: int
    killed: bool = False
    timed_out: bool = False
    duration_ms: float | None = None
    command: str | None = None


# =============================================================================
# BashTool
# =============================================================================


class BashTool(BaseTool):
    """Tool for executing bash commands.

    Provides secure command execution with permission checking,
    security validation, timeout handling, and progress reporting.
    """

    aliases: list[str] | None = None
    search_hint: str | None = "run a bash command"
    max_result_size_chars: int = 100_000
    strict: bool = False
    should_defer: bool = False
    always_load: bool = False

    @property
    def name(self) -> str:
        return BASH_TOOL_NAME

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "description": {
                    "type": "string",
                    "description": "A brief description of what the command does",
                },
                "timeout": {
                    "type": "integer",
                    "description": (
                        "Timeout in milliseconds. "
                        "Default is 60 seconds, max is 600 seconds."
                    ),
                },
                "working_directory": {
                    "type": "string",
                    "description": "The directory to execute the command in",
                },
            },
            "required": ["command"],
        }

    def is_concurrency_safe(self, input: Any) -> bool:
        return False

    def is_read_only(self, input: Any) -> bool:
        return _check_is_read_only(input.get("command", ""))

    def is_destructive(self, input: Any) -> bool:
        return _check_is_destructive(input.get("command", ""))

    def is_search_or_read_command(self, input: Any) -> dict[str, bool]:
        command = input.get("command", "")
        return is_search_or_read_bash_command(command)

    def get_path(self, input: Any) -> str | None:
        command = input.get("command", "")
        # Extract path from commands like 'cd /path'
        parts = command.split()
        if len(parts) >= 2 and parts[0] in ("cd", "ls", "cat", "head", "tail"):
            path = parts[1]
            if os.path.isabs(path) and isinstance(path, str):
                return path
        return None

    def to_auto_classifier_input(self, input: Any) -> str:
        command = input.get("command", "")
        # Strip safe wrappers for classification
        stripped = strip_safe_wrappers(command)
        return stripped

    async def validate_input(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate the tool input before execution."""
        command = input.get("command")
        if not command:
            return (False, "command is required", 400)

        if not isinstance(command, str):
            return (False, "command must be a string", 400)

        if len(command.strip()) == 0:
            return (False, "command cannot be empty", 400)

        # Security check using shell-quote
        security_result = bash_command_is_safe(command)
        if security_result["behavior"] == "ask":
            return (
                False,
                security_result.get("message", "Security check failed"),
                400,
            )

        return True

    async def check_permissions(
        self,
        input: Any,
        context: ToolUseContext,
    ) -> PermissionAskResult:
        """Check if the user has permission to run this command."""
        command = input.get("command", "")

        # Check if this is a git command
        if is_normalized_git_command(command):
            return PermissionAskResult(
                behavior="ask",
                message=f"Permission to run git command: {command[:100]}",
            )

        # Check if this is a cd command
        if is_normalized_cd_command(command):
            return PermissionAskResult(
                behavior="ask",
                message=f"Permission to change directory: {command[:100]}",
            )

        # Default: passthrough for other commands
        return PermissionAskResult(behavior="ask", message="Permission required")

    async def call(
        self,
        args: Any,
        context: ToolUseContext,
        can_use_tool: Any,
        parent_message: Any,
        on_progress: Any = None,
    ) -> ToolResult[BashToolOutput]:
        """Execute the bash tool.

        Args:
            args: Tool input with command and options.
            context: Execution context.
            can_use_tool: Permission checking function.
            parent_message: Parent assistant message.
            on_progress: Optional progress callback.

        Returns:
            ToolResult with command execution result.
        """
        command = args.get("command", "")
        timeout_ms = args.get("timeout")
        working_dir = args.get("working_directory")

        start_time = time.perf_counter()

        # Convert timeout to seconds
        timeout_seconds = 60.0
        if timeout_ms:
            timeout_seconds = min(timeout_ms / 1000.0, 600.0)
        elif context.abort_controller:
            # Use a default timeout if not specified
            timeout_seconds = 60.0

        # Determine working directory
        cwd = working_dir or os.getcwd()

        # Set up environment
        env = os.environ.copy()

        # Report progress for long-running commands
        async def progress_task() -> None:
            if on_progress:
                await asyncio.sleep(PROGRESS_THRESHOLD_MS / 1000.0)
                progress_data = {
                    "type": "bash",
                    "command": command[:200],
                    "working_directory": cwd,
                }
                on_progress(progress_data)

        progress_coro = asyncio.create_task(progress_task())

        # Execute command
        stdout = ""
        stderr = ""
        exit_code = -1
        killed = False
        timed_out = False

        try:
            # Check for abort signal
            if context.abort_controller and hasattr(context.abort_controller, "signal"):
                loop = asyncio.get_event_loop()
                with contextlib.suppress(OSError, AttributeError):
                    loop.add_signal_handler(
                        15,  # SIGINT
                        lambda: None,
                    )

            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    result.communicate(), timeout=timeout_seconds
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
                stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
                exit_code = result.returncode if result.returncode is not None else -1
            except TimeoutError:
                result.kill()
                await result.wait()
                timed_out = True
                killed = True
                exit_code = 124  # Standard timeout exit code
                stderr = f"Command timed out after {timeout_seconds} seconds."

        except asyncio.CancelledError:
            killed = True
            exit_code = 130
        except Exception as e:
            stderr = str(e)
            exit_code = 1
        finally:
            progress_coro.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await progress_coro

        duration_ms = (time.perf_counter() - start_time) * 1000

        output = BashToolOutput(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            killed=killed,
            timed_out=timed_out,
            duration_ms=round(duration_ms, 2),
            command=command,
        )

        return ToolResult(data=output)

    async def description(self, input: Any, options: dict[str, Any]) -> str:
        command = input.get("command", "") if input else ""
        return f"Claude wants to execute: {command[:100]}"

    async def prompt(self, options: dict[str, Any]) -> str:
        return (
            "The Bash tool executes shell commands. "
            "Use it for git operations, file manipulation, running tests, "
            "starting servers, and other command-line operations. "
            "Provide the command to execute and an optional description. "
            "Use timeout to set a maximum execution time."
        )


# =============================================================================
# Helper Functions
# =============================================================================


def is_search_or_read_bash_command(command: str) -> dict[str, bool]:
    """Check if a bash command is a search or read operation.

    Args:
        command: The shell command string.

    Returns:
        Dict with isSearch, isRead, and isList flags.
    """
    try:
        parts_with_operators = split_command(command)
    except Exception:
        return {"is_search": False, "is_read": False, "is_list": False}

    if not parts_with_operators:
        return {"is_search": False, "is_read": False, "is_list": False}

    has_search = False
    has_read = False
    has_list = False
    has_non_neutral = False

    for part in parts_with_operators:
        if part in ("&&", "||", "|", ";", ">", ">>", "<"):
            continue

        tokens = part.strip().split()
        if not tokens:
            continue

        base_command = tokens[0]
        if base_command in BASH_SEMANTIC_NEUTRAL_COMMANDS:
            continue

        has_non_neutral = True

        if base_command in BASH_SEARCH_COMMANDS:
            has_search = True
        if base_command in BASH_READ_COMMANDS:
            has_read = True
        if base_command in BASH_LIST_COMMANDS:
            has_list = True

    return {
        "is_search": has_search,
        "is_read": has_read or (has_non_neutral and not has_search),
        "is_list": has_list,
    }


def _check_is_read_only(command: str) -> bool:
    """Check if a command is read-only."""
    result = is_search_or_read_bash_command(command)
    return result["is_search"] or result["is_read"] or result["is_list"]


def _check_is_destructive(command: str) -> bool:
    """Check if a command is potentially destructive."""
    dangerous = frozenset([
        "rm",
        "rmdir",
        "dd",
        "mkfs",
        "fdisk",
        "parted",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
    ])

    try:
        parts = split_command(command)
        for part in parts:
            tokens = part.strip().split()
            if tokens and tokens[0] in dangerous:
                # Check for -rf flags
                for token in tokens[1:]:
                    if token in ("-rf", "-r", "-f", "-rfz", "-rf /"):
                        return True
    except Exception:
        pass

    return False
