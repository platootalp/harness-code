"""Child CLI session spawning for Remote Control sessions.

Handles spawning child Claude Code processes with the SDK transport,
managing their lifecycle, and forwarding permission requests.

TypeScript equivalent: src/bridge/sessionRunner.ts
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# =============================================================================
# Types
# =============================================================================


class SessionDoneStatus(StrEnum):
    """Status of a child session."""

    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ActivityType(StrEnum):
    """Type of session activity."""

    TOOL_START = "tool_start"
    TEXT = "text"
    RESULT = "result"
    ERROR = "error"


@dataclass
class ToolStartActivity:
    """A tool invocation started."""

    type: str = "tool_start"
    summary: str = ""
    timestamp: int = 0


@dataclass
class TextActivity:
    """Text content from the assistant."""

    type: str = "text"
    summary: str = ""
    timestamp: int = 0


@dataclass
class ResultActivity:
    """Session result."""

    type: str = "result"
    summary: str = ""
    timestamp: int = 0


@dataclass
class ErrorActivity:
    """Session error."""

    type: str = "error"
    summary: str = ""
    timestamp: int = 0


SessionActivity = ToolStartActivity | TextActivity | ResultActivity | ErrorActivity


@dataclass
class PermissionRequest:
    """A control_request emitted by the child CLI for permission checks."""

    type: str = "control_request"
    request_id: str = ""
    request: dict[str, Any] | None = None


# =============================================================================
# Tool Verb Mapping
# =============================================================================

TOOL_VERBS: dict[str, str] = {
    "Read": "Reading",
    "Write": "Writing",
    "Edit": "Editing",
    "MultiEdit": "Editing",
    "Bash": "Running",
    "Glob": "Searching",
    "Grep": "Searching",
    "WebFetch": "Fetching",
    "WebSearch": "Searching",
    "Task": "Running task",
    "FileReadTool": "Reading",
    "FileWriteTool": "Writing",
    "FileEditTool": "Editing",
    "GlobTool": "Searching",
    "GrepTool": "Searching",
    "BashTool": "Running",
    "NotebookEditTool": "Editing notebook",
    "LSP": "LSP",
}


# =============================================================================
# Utilities
# =============================================================================


def safe_filename_id(id: str) -> str:
    """Sanitize a session ID for use in file names.

    Strips any characters that could cause path traversal or other
    filesystem issues, replacing them with underscores.

    Args:
        id: The session ID to sanitize.

    Returns:
        A sanitized string safe for use in file names.
    """
    return re.sub(r"[^a-zA-Z0-9_-]", "_", id)


def _tool_summary(name: str, input_dict: dict[str, Any]) -> str:
    """Build a short description of a tool invocation."""
    verb = TOOL_VERBS.get(name, name)
    target: str | None = None
    for key in ("file_path", "filePath", "pattern", "command", "url", "query"):
        if key in input_dict:
            val = input_dict[key]
            if isinstance(val, str):
                target = val
                break
    if target:
        return f"{verb} {target}"
    return verb


def _input_preview(input_dict: dict[str, Any]) -> str:
    """Build a short preview of tool input for debug logging."""
    parts: list[str] = []
    for key, val in list(input_dict.items())[:3]:
        if isinstance(val, str):
            parts.append(f'{key}="{val[:100]}"')
    return " ".join(parts)


def _safe_json_parse(raw: str) -> dict[str, Any] | None:
    """Parse JSON safely."""
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
        return None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


# =============================================================================
# Activity Extraction
# =============================================================================


def extract_activities(
    line: str,
    session_id: str,
    on_debug: Callable[[str], None],
) -> list[SessionActivity]:
    """Parse NDJSON line from child stdout and extract session activities.

    Args:
        line: Raw NDJSON line from child process stdout.
        session_id: The session ID for debug logging.
        on_debug: Debug logging callback.

    Returns:
        List of SessionActivity objects extracted from the line.
    """
    parsed = _safe_json_parse(line)
    if not parsed:
        return []

    msg = parsed
    activities: list[SessionActivity] = []
    now = _time_ms()

    msg_type = msg.get("type")
    if msg_type == "assistant":
        message = msg.get("message")
        if not isinstance(message, dict):
            return []
        content = message.get("content")
        if not isinstance(content, list):
            return []

        for block in content:
            if not isinstance(block, dict):
                continue

            block_type = block.get("type")
            if block_type == "tool_use":
                name = block.get("name", "Tool")
                input_dict = block.get("input", {})
                summary = _tool_summary(name, input_dict)
                activities.append(
                    ToolStartActivity(
                        type="tool_start",
                        summary=summary,
                        timestamp=now,
                    )
                )
                on_debug(
                    f"[bridge:activity] sessionId={session_id} "
                    f"tool_use name={name} {_input_preview(input_dict)}"
                )
            elif block_type == "text":
                text = block.get("text", "")
                if text:
                    activities.append(
                        TextActivity(
                            type="text",
                            summary=text[:80],
                            timestamp=now,
                        )
                    )
                    on_debug(
                        f"[bridge:activity] sessionId={session_id} "
                        f'text "{text[:100]}"'
                    )

    elif msg_type == "result":
        subtype = msg.get("subtype")
        if subtype == "success":
            activities.append(
                ResultActivity(
                    type="result",
                    summary="Session completed",
                    timestamp=now,
                )
            )
            on_debug(
                f"[bridge:activity] sessionId={session_id} result subtype=success"
            )
        elif subtype:
            errors = msg.get("errors")
            if isinstance(errors, list) and errors:
                error_summary = errors[0]
            else:
                error_summary = f"Error: {subtype}"
            activities.append(
                ErrorActivity(
                    type="error",
                    summary=error_summary,
                    timestamp=now,
                )
            )
            on_debug(
                f"[bridge:activity] sessionId={session_id} "
                f"result subtype={subtype} error=\"{error_summary}\""
            )
        else:
            on_debug(
                f"[bridge:activity] sessionId={session_id} "
                "result subtype=undefined"
            )

    return activities


def extract_user_message_text(
    msg: dict[str, Any],
) -> str | None:
    """Extract plain text from a user message NDJSON line.

    Returns trimmed text if this looks like a real human-authored message,
    otherwise None (skipping tool-result messages, synthetic messages, etc.).

    Args:
        msg: Parsed NDJSON message dict.

    Returns:
        The message text, or None if this is not a real user message.
    """
    # Skip tool-result user messages and synthetic/replay
    if (
        msg.get("parent_tool_use_id") is not None
        or msg.get("isSynthetic")
        or msg.get("isReplay")
    ):
        return None

    message = msg.get("message")
    if not isinstance(message, dict):
        return None

    content = message.get("content")
    text: str | None = None

    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                break

    text = text.strip() if isinstance(text, str) else None
    return text if text else None


# =============================================================================
# Time dependency
# =============================================================================


def _time_ms() -> int:
    return int(time.time() * 1000)


def _set_time_ms(fn: Callable[[], int]) -> None:
    """Override time_ms for testing."""
    global _time_ms
    _time_ms = fn
