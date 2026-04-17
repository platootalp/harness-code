"""
Tests for cli/state.py - REPL state management.
"""

from __future__ import annotations

import pytest
from claude_code.cli.state import (
    PermissionMode,
    PromptInputMode,
    REPLState,
    SessionState,
    add_message,
    add_to_history,
    append_stream_text,
    clear_messages,
    get_messages,
    get_repl_state,
    get_stream_text,
    history_next,
    history_previous,
    reset_repl_state,
    set_compressing,
    set_debug,
    set_input_mode,
    set_permission_mode,
    set_streaming,
)


class TestPromptInputMode:
    """Tests for PromptInputMode enum."""

    def test_values(self) -> None:
        """Test all input modes exist."""
        assert PromptInputMode.PROMPT.value == "prompt"
        assert PromptInputMode.EDIT.value == "edit"
        assert PromptInputMode.VIM_NORMAL.value == "vim_normal"
        assert PromptInputMode.VIM_INSERT.value == "vim_insert"
        assert PromptInputMode.COMMAND.value == "command"


class TestPermissionMode:
    """Tests for PermissionMode enum."""

    def test_values(self) -> None:
        """Test all permission modes exist."""
        assert PermissionMode.AUTO.value == "auto"
        assert PermissionMode.BYPASS.value == "bypassPermissions"
        assert PermissionMode.DENY.value == "deny"


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        state = SessionState()
        assert state.session_id is None
        assert state.model == "claude-sonnet-4-20250514"
        assert state.system_prompt is None
        assert state.resume_id is None
        assert state.created_at is None

    def test_with_values(self) -> None:
        """Test with provided values."""
        state = SessionState(
            session_id="sess_123",
            model="claude-3-5-haiku",
            system_prompt="You are helpful.",
            resume_id="resume_456",
            created_at=1234567890.0,
        )
        assert state.session_id == "sess_123"
        assert state.model == "claude-3-5-haiku"
        assert state.system_prompt == "You are helpful."
        assert state.resume_id == "resume_456"
        assert state.created_at == 1234567890.0


class TestREPLState:
    """Tests for REPLState dataclass."""

    def test_defaults(self) -> None:
        """Test default values."""
        state = REPLState()
        assert isinstance(state.session, SessionState)
        assert state.messages == []
        assert state.input_mode == PromptInputMode.PROMPT
        assert state.cursor_offset == 0
        assert state.current_input == ""
        assert state.is_streaming is False
        assert state.is_compressing is False
        assert state.stream_text == ""
        assert state.permission_mode == PermissionMode.AUTO
        assert state.mcp_servers == {}
        assert state.mcp_loading is False
        assert state.bridge_connected is False
        assert state.bridge_reconnecting is False
        assert state.team_context is None
        assert state.command_history == []
        assert state.history_index == -1
        assert state.debug_enabled is False
        assert state.output_format == "text"
        assert state.continue_session is False


class TestGlobalState:
    """Tests for global state functions."""

    def setup_method(self) -> None:
        """Reset state before each test."""
        reset_repl_state()

    def test_get_repl_state(self) -> None:
        """Test getting the global state."""
        state = get_repl_state()
        assert isinstance(state, REPLState)

    def test_reset_repl_state(self) -> None:
        """Test resetting the global state."""
        state1 = get_repl_state()
        state1.current_input = "test"
        state2 = reset_repl_state()
        assert state2 is not state1
        assert state2.current_input == ""

    def test_add_message(self) -> None:
        """Test adding a message."""
        add_message({"role": "user", "content": "hello"})
        messages = get_messages()
        assert len(messages) == 1
        assert messages[0]["content"] == "hello"

    def test_clear_messages(self) -> None:
        """Test clearing messages."""
        add_message({"role": "user", "content": "hello"})
        clear_messages()
        assert get_messages() == []

    def test_add_to_history(self) -> None:
        """Test adding to command history."""
        add_to_history("ls")
        add_to_history("cd /tmp")
        state = get_repl_state()
        assert state.command_history == ["ls", "cd /tmp"]
        assert state.history_index == 2

    def test_add_to_history_dedup(self) -> None:
        """Test that duplicate history entries are moved to end."""
        add_to_history("ls")
        add_to_history("cd /tmp")
        add_to_history("ls")  # Move existing to end
        state = get_repl_state()
        assert state.command_history == ["cd /tmp", "ls"]
        assert state.history_index == 2

    def test_history_previous(self) -> None:
        """Test navigating history with previous()."""
        add_to_history("ls")
        add_to_history("cd /tmp")
        get_repl_state().history_index = len(get_repl_state().command_history)
        result = history_previous()
        assert result == "cd /tmp"

    def test_history_previous_empty(self) -> None:
        """Test history_previous with empty history."""
        result = history_previous()
        assert result is None

    def test_history_next(self) -> None:
        """Test navigating history with next()."""
        add_to_history("ls")
        add_to_history("cd /tmp")
        get_repl_state().history_index = 0  # Go to start
        result = history_next()
        assert result == "cd /tmp"

    def test_history_next_at_end(self) -> None:
        """Test history_next when at end returns empty."""
        add_to_history("ls")
        get_repl_state().history_index = 0
        result = history_next()
        assert result == ""


class TestStreamingHelpers:
    """Tests for streaming state helpers."""

    def setup_method(self) -> None:
        reset_repl_state()

    def test_set_streaming(self) -> None:
        """Test setting streaming state."""
        set_streaming(True)
        assert get_repl_state().is_streaming is True

    def test_set_streaming_false_clears_text(self) -> None:
        """Test that disabling streaming clears accumulated text."""
        append_stream_text("Hello")
        set_streaming(False)
        assert get_repl_state().is_streaming is False
        assert get_stream_text() == ""

    def test_append_stream_text(self) -> None:
        """Test appending to stream text."""
        append_stream_text("Hello ")
        append_stream_text("World")
        assert get_stream_text() == "Hello World"

    def test_get_stream_text_empty(self) -> None:
        """Test getting empty stream text."""
        assert get_stream_text() == ""


class TestInputModeHelpers:
    """Tests for input mode helpers."""

    def setup_method(self) -> None:
        reset_repl_state()

    def test_set_input_mode(self) -> None:
        """Test setting input mode."""
        set_input_mode(PromptInputMode.VIM_INSERT)
        assert get_repl_state().input_mode == PromptInputMode.VIM_INSERT

    def test_set_input_mode_from_string(self) -> None:
        """Test setting input mode from string value."""
        set_input_mode(PromptInputMode("edit"))  # type: ignore
        assert get_repl_state().input_mode == PromptInputMode.EDIT


class TestPermissionModeHelpers:
    """Tests for permission mode helpers."""

    def setup_method(self) -> None:
        reset_repl_state()

    def test_set_permission_mode(self) -> None:
        """Test setting permission mode."""
        set_permission_mode(PermissionMode.BYPASS)
        assert get_repl_state().permission_mode == PermissionMode.BYPASS

    def test_set_permission_mode_from_string(self) -> None:
        """Test setting permission mode from string."""
        set_permission_mode("bypassPermissions")
        assert get_repl_state().permission_mode == PermissionMode.BYPASS

    def test_set_permission_mode_from_auto_string(self) -> None:
        """Test setting permission mode from 'auto' string."""
        set_permission_mode("auto")
        assert get_repl_state().permission_mode == PermissionMode.AUTO


class TestDebugHelpers:
    """Tests for debug helpers."""

    def setup_method(self) -> None:
        reset_repl_state()

    def test_set_debug(self) -> None:
        """Test setting debug mode."""
        set_debug(True)
        assert get_repl_state().debug_enabled is True

    def test_set_debug_false(self) -> None:
        """Test disabling debug mode."""
        get_repl_state().debug_enabled = True
        set_debug(False)
        assert get_repl_state().debug_enabled is False


class TestCompressingHelpers:
    """Tests for compressing state helpers."""

    def setup_method(self) -> None:
        reset_repl_state()

    def test_set_compressing(self) -> None:
        """Test setting compressing state."""
        set_compressing(True)
        assert get_repl_state().is_compressing is True

    def test_set_compressing_false(self) -> None:
        """Test disabling compressing state."""
        get_repl_state().is_compressing = True
        set_compressing(False)
        assert get_repl_state().is_compressing is False
