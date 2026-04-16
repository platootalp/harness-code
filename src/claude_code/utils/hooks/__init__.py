"""
Hooks utilities package - lifecycle hooks for command execution.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import platform
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .hooks_config_snapshot import (
    get_hooks_config_snapshot,
    restore_hooks_config_snapshot,
    take_hooks_config_snapshot,
    update_hooks_config_snapshot,
)

# =============================================================================
# Hook Event Types
# =============================================================================


class HookEvent(StrEnum):
    """Enumeration of hook event types."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    SETUP = "Setup"
    STOP = "Stop"
    STOP_FAILURE = "StopFailure"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    TASK_CREATED = "TaskCreated"
    TASK_COMPLETED = "TaskCompleted"
    CONFIG_CHANGE = "ConfigChange"
    CWD_CHANGED = "CwdChanged"
    FILE_CHANGED = "FileChanged"
    INSTRUCTIONS_LOADED = "InstructionsLoaded"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PERMISSION_REQUEST = "PermissionRequest"
    ELICITATION = "Elicitation"
    ELICITATION_RESULT = "ElicitationResult"


# =============================================================================
# Hook Command
# =============================================================================


@dataclass
class HookCommand:
    """A hook command to execute."""

    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    timeout_ms: int = 30000


# =============================================================================
# Hook Result
# =============================================================================


@dataclass
class HookResult:
    """Result of a hook execution."""

    message: str | None = None
    system_message: str | None = None
    blocking_error: str | None = None
    outcome: str = "success"
    prevent_continuation: bool = False
    stop_reason: str | None = None
    permission_behavior: str | None = None
    additional_context: str | None = None
    updated_input: dict[str, Any] | None = None
    watch_paths: list[str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HookResult:
        """Create a HookResult from a dictionary."""
        return cls(
            message=data.get("message"),
            system_message=data.get("systemMessage"),
            blocking_error=data.get("blockingError"),
            outcome=data.get("outcome", "success"),
            prevent_continuation=data.get("preventContinuation", False),
            stop_reason=data.get("stopReason"),
            permission_behavior=data.get("permissionBehavior"),
            additional_context=data.get("additionalContext"),
            updated_input=data.get("updatedInput"),
            watch_paths=data.get("watchPaths"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        result: dict[str, Any] = {"outcome": self.outcome}
        if self.message is not None:
            result["message"] = self.message
        if self.system_message is not None:
            result["systemMessage"] = self.system_message
        if self.blocking_error is not None:
            result["blockingError"] = self.blocking_error
        if self.prevent_continuation:
            result["preventContinuation"] = True
        if self.stop_reason is not None:
            result["stopReason"] = self.stop_reason
        if self.permission_behavior is not None:
            result["permissionBehavior"] = self.permission_behavior
        if self.additional_context is not None:
            result["additionalContext"] = self.additional_context
        if self.updated_input is not None:
            result["updatedInput"] = self.updated_input
        if self.watch_paths is not None:
            result["watchPaths"] = self.watch_paths
        return result


# =============================================================================
# Base Hook Input
# =============================================================================


def create_base_hook_input(
    permission_mode: str | None = None,
    session_id: str | None = None,
    agent_info: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create base hook input common to all hook types."""
    return {
        "permissionMode": permission_mode,
        "sessionId": session_id,
        "agentInfo": agent_info or {},
    }


# =============================================================================
# Trust Verification
# =============================================================================


def is_workspace_trusted() -> bool:
    """Check if the workspace has been trusted."""
    return os.environ.get("CLAUDE_TRUSTED", "") == "1"


def is_non_interactive() -> bool:
    """Check if running in non-interactive/SDK mode."""
    return os.environ.get("CLAUDE_SDK", "") == "1"


def should_skip_hook_due_to_trust() -> bool:
    """Check if hook should be skipped due to lack of workspace trust."""
    if is_non_interactive():
        return False
    return not is_workspace_trusted()


# =============================================================================
# Hook Output Parsing
# =============================================================================


def parse_hook_output(stdout: str) -> dict[str, Any]:
    """Parse and validate JSON hook output."""
    stdout = stdout.strip()
    if not stdout:
        return {"outcome": "success"}
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            return data
        return {"outcome": "success"}
    except json.JSONDecodeError:
        return {"outcome": "success"}


# =============================================================================
# Command Hook Execution
# =============================================================================


async def exec_command_hook(
    hook: HookCommand,
    hook_event: HookEvent,
    hook_name: str,
    json_input: str,
    signal: asyncio.AbstractEventLoop | None = None,
    hook_id: str | None = None,
) -> dict[str, Any]:
    """Execute a command-based hook using bash or PowerShell."""
    env = {**os.environ}
    if hook.env:
        env.update(hook.env)
    env["CLAUDE_HOOK_EVENT"] = str(hook_event.value)
    env["CLAUDE_HOOK_NAME"] = hook_name
    if hook_id:
        env["CLAUDE_HOOK_ID"] = hook_id

    timeout_sec = hook.timeout_ms / 1000.0

    try:
        shell_cmd: list[str]
        if platform.system() == "Windows":
            shell_cmd = ["powershell", "-Command", f"{hook.command} {''.join(hook.args)}"]
        else:
            shell_cmd = ["/bin/sh", "-c", f"{hook.command} {' '.join(hook.args)}"]

        proc = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=json_input.encode("utf-8")),
            timeout=timeout_sec,
        )

        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode("utf-8", errors="replace")
            return {
                "outcome": "error",
                "blockingError": f"Hook failed: {stderr_text[:500]}",
            }

        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        return parse_hook_output(stdout_text)

    except TimeoutError:
        return {
            "outcome": "error",
            "blockingError": f"Hook timed out after {hook.timeout_ms}ms",
        }
    except OSError as e:
        return {
            "outcome": "error",
            "blockingError": f"Hook execution failed: {str(e)[:200]}",
        }


# =============================================================================
# Async Hook Registry
# =============================================================================


_hook_registry: dict[str, list[HookCommand]] = {}


def register_hook(event: HookEvent, command: HookCommand) -> None:
    """Register a hook command for an event."""
    event_name = event.value
    if event_name not in _hook_registry:
        _hook_registry[event_name] = []
    _hook_registry[event_name].append(command)


def unregister_hook(event: HookEvent, command: HookCommand) -> None:
    """Unregister a hook command."""
    event_name = event.value
    if event_name in _hook_registry:
        with contextlib.suppress(ValueError):
            _hook_registry[event_name].remove(command)


def get_hooks_for_event(event: HookEvent) -> list[HookCommand]:
    """Get all registered hooks for an event."""
    return list(_hook_registry.get(event.value, []))


def clear_hooks() -> None:
    """Clear all registered hooks."""
    _hook_registry.clear()


# =============================================================================
# Hook Execution Helper
# =============================================================================


async def run_hooks_for_event(
    event: HookEvent,
    hook_input: dict[str, Any],
    hook_name: str | None = None,
) -> list[HookResult]:
    """Run all hooks for a given event."""
    if should_skip_hook_due_to_trust():
        return []

    hooks = get_hooks_for_event(event)
    json_input = json.dumps(hook_input, ensure_ascii=False)
    results: list[HookResult] = []

    for hook in hooks:
        result_dict = await exec_command_hook(
            hook,
            event,
            hook_name or event.value,
            json_input,
            hook_id=event.value,
        )
        results.append(HookResult.from_dict(result_dict))

    return results


# =============================================================================
# Hooks Config Snapshot
# =============================================================================

__all__ = [
    "HookCommand",
    "HookEvent",
    "HookResult",
    "clear_hooks",
    "create_base_hook_input",
    "exec_command_hook",
    "get_hooks_config_snapshot",
    "get_hooks_for_event",
    "is_non_interactive",
    "is_workspace_trusted",
    "parse_hook_output",
    "register_hook",
    "restore_hooks_config_snapshot",
    "run_hooks_for_event",
    "should_skip_hook_due_to_trust",
    "take_hooks_config_snapshot",
    "unregister_hook",
    "update_hooks_config_snapshot",
]
