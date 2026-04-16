"""
REPL state management.

TypeScript equivalent: src/state/AppStateStore.ts

Provides the application state for the REPL including:
- Session management
- Message history
- Input modes
- Streaming state
- MCP server connections
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Input Mode
# =============================================================================


class PromptInputMode(StrEnum):
    """Input mode for the prompt."""

    PROMPT = "prompt"  # Normal input
    EDIT = "edit"  # Editing mode
    VIM_NORMAL = "vim_normal"
    VIM_INSERT = "vim_insert"
    COMMAND = "command"  # Slash command mode


# =============================================================================
# Permission Mode
# =============================================================================


class PermissionMode(StrEnum):
    """Permission mode for tool execution."""

    AUTO = "auto"  # Ask for sensitive operations
    BYPASS = "bypassPermissions"  # Allow all
    DENY = "deny"  # Deny all


# =============================================================================
# Session State
# =============================================================================


@dataclass
class SessionState:
    """State for the current session."""

    session_id: str | None = None
    model: str = "claude-sonnet-4-20250514"
    system_prompt: str | None = None
    resume_id: str | None = None
    created_at: float | None = None  # Unix timestamp


# =============================================================================
# REPL State
# =============================================================================


@dataclass
class REPLState:
    """State for the REPL application.

    TypeScript equivalent: AppState in src/state/AppStateStore.ts
    """

    # Session
    session: SessionState = field(default_factory=SessionState)

    # Messages
    messages: list[Any] = field(default_factory=list)  # list[Message]

    # Input state
    input_mode: PromptInputMode = PromptInputMode.PROMPT
    cursor_offset: int = 0
    current_input: str = ""

    # Streaming state
    is_streaming: bool = False
    is_compressing: bool = False  # Context compression in progress
    stream_text: str = ""  # Accumulated streaming text

    # Permission mode
    permission_mode: PermissionMode = PermissionMode.AUTO

    # MCP
    mcp_servers: dict[str, Any] = field(default_factory=dict)
    mcp_loading: bool = False

    # Bridge
    bridge_connected: bool = False
    bridge_reconnecting: bool = False

    # Team
    team_context: dict[str, Any] | None = None

    # History
    command_history: list[str] = field(default_factory=list)
    history_index: int = -1  # -1 means at end of history

    # Debug
    debug_enabled: bool = False

    # Output format
    output_format: str = "text"

    # Continuation
    continue_session: bool = False


# =============================================================================
# Global state instance
# =============================================================================

_repl_state = REPLState()


def get_repl_state() -> REPLState:
    """Get the global REPL state instance.

    Returns:
        The global REPLState instance.
    """
    return _repl_state


def reset_repl_state() -> REPLState:
    """Reset the global REPL state to defaults.

    Returns:
        A new REPLState instance.
    """
    global _repl_state
    _repl_state = REPLState()
    return _repl_state


# =============================================================================
# State helpers
# =============================================================================


def add_message(message: Any) -> None:
    """Add a message to the REPL state.

    Args:
        message: Message to add.
    """
    _repl_state.messages.append(message)


def get_messages() -> list[Any]:
    """Get all messages from REPL state.

    Returns:
        List of messages.
    """
    return list(_repl_state.messages)


def clear_messages() -> None:
    """Clear all messages from REPL state."""
    _repl_state.messages.clear()


def add_to_history(command: str) -> None:
    """Add a command to history.

    Args:
        command: Command to add.
    """
    if command in _repl_state.command_history:
        # Move existing entry to end
        _repl_state.command_history.remove(command)
    _repl_state.command_history.append(command)
    _repl_state.history_index = len(_repl_state.command_history)


def get_history_at_index(index: int) -> str | None:
    """Get command at history index.

    Args:
        index: History index.

    Returns:
        Command string or None.
    """
    if 0 <= index < len(_repl_state.command_history):
        return _repl_state.command_history[index]
    return None


def history_previous() -> str | None:
    """Move to previous history item.

    Returns:
        Previous command or None.
    """
    if not _repl_state.command_history:
        return None

    if _repl_state.history_index < 0:
        _repl_state.history_index = len(_repl_state.command_history) - 1
    elif _repl_state.history_index > 0:
        _repl_state.history_index -= 1

    return get_history_at_index(_repl_state.history_index)


def history_next() -> str | None:
    """Move to next history item.

    Returns:
        Next command or None.
    """
    if not _repl_state.command_history:
        return None

    if _repl_state.history_index < len(_repl_state.command_history) - 1:
        _repl_state.history_index += 1
    else:
        _repl_state.history_index = len(_repl_state.command_history)

    if _repl_state.history_index >= len(_repl_state.command_history):
        return ""

    return get_history_at_index(_repl_state.history_index)


def set_streaming(streaming: bool) -> None:
    """Set streaming state.

    Args:
        streaming: Whether streaming is active.
    """
    _repl_state.is_streaming = streaming
    if not streaming:
        _repl_state.stream_text = ""


def append_stream_text(text: str) -> None:
    """Append text to accumulated stream.

    Args:
        text: Text to append.
    """
    _repl_state.stream_text += text


def get_stream_text() -> str:
    """Get accumulated stream text.

    Returns:
        Accumulated stream text.
    """
    return _repl_state.stream_text


def set_input_mode(mode: PromptInputMode) -> None:
    """Set the input mode.

    Args:
        mode: New input mode.
    """
    _repl_state.input_mode = mode


def set_permission_mode(mode: PermissionMode | str) -> None:
    """Set the permission mode.

    Args:
        mode: New permission mode.
    """
    if isinstance(mode, str):
        mode = PermissionMode(mode)
    _repl_state.permission_mode = mode


def set_debug(enabled: bool) -> None:
    """Set debug mode.

    Args:
        enabled: Whether debug mode is enabled.
    """
    _repl_state.debug_enabled = enabled


def set_compressing(compressing: bool) -> None:
    """Set compressing state.

    Args:
        compressing: Whether compression is in progress.
    """
    _repl_state.is_compressing = compressing
