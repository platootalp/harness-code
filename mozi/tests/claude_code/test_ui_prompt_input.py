"""
Tests for UI prompt input components.
"""

from __future__ import annotations

import pytest

from claude_code.ui.prompt_input import (
    PromptInput,
    PromptInputFooter,
    PromptInputMode,
    PromptInputState,
    PromptInputSuggestion,
    SuggestionType,
    VimMode,
)


# =============================================================================
# PromptInputMode Tests
# =============================================================================


class TestPromptInputMode:
    """Tests for PromptInputMode."""

    def test_values(self) -> None:
        """Test mode values."""
        assert PromptInputMode.EDIT.value == "edit"
        assert PromptInputMode.VIM_NORMAL.value == "vim_normal"
        assert PromptInputMode.VIM_INSERT.value == "vim_insert"
        assert PromptInputMode.VIM_VISUAL.value == "vim_visual"


# =============================================================================
# VimMode Tests
# =============================================================================


class TestVimMode:
    """Tests for VimMode enum."""

    def test_values(self) -> None:
        """Test vim mode values."""
        assert VimMode.NORMAL.value == "normal"
        assert VimMode.INSERT.value == "insert"
        assert VimMode.VISUAL.value == "visual"
        assert VimMode.COMMAND.value == "command"


# =============================================================================
# SuggestionType Tests
# =============================================================================


class TestSuggestionType:
    """Tests for SuggestionType."""

    def test_values(self) -> None:
        """Test suggestion type values."""
        assert SuggestionType.COMMAND.value == "command"
        assert SuggestionType.FILE.value == "file"
        assert SuggestionType.SEARCH.value == "search"
        assert SuggestionType.HISTORY.value == "history"


# =============================================================================
# PromptInputSuggestion Tests
# =============================================================================


class TestPromptInputSuggestion:
    """Tests for PromptInputSuggestion."""

    def test_create(self) -> None:
        """Test creating a suggestion."""
        s = PromptInputSuggestion(
            type=SuggestionType.COMMAND,
            text="/help",
            description="Show help",
        )
        assert s.type == SuggestionType.COMMAND
        assert s.text == "/help"
        assert s.description == "Show help"
        assert s.is_selected is False
        assert s.score == 0

    def test_with_score(self) -> None:
        """Test suggestion with match score."""
        s = PromptInputSuggestion(
            type=SuggestionType.COMMAND,
            text="/help",
            description="Show help",
            score=95,
        )
        assert s.score == 95

    def test_update_selection(self) -> None:
        """Test updating selection state."""
        s = PromptInputSuggestion(
            type=SuggestionType.COMMAND,
            text="/help",
            description="Show help",
        )
        s.update_selection(True)
        assert s.is_selected is True
        s.update_selection(False)
        assert s.is_selected is False


# =============================================================================
# PromptInputState Tests
# =============================================================================


class TestPromptInputState:
    """Tests for PromptInputState."""

    def test_create(self) -> None:
        """Test creating prompt input state."""
        state = PromptInputState()
        assert state.value == ""
        assert state.cursor_position == 0
        assert state.mode == PromptInputMode.EDIT
        assert state.show_suggestions is False
        assert state.suggestion_index == 0
        assert state.history_index == -1
        assert state.is_multiline is False

    def test_with_initial_value(self) -> None:
        """Test state with initial value."""
        state = PromptInputState(value="Hello world", cursor_position=5)
        assert state.value == "Hello world"
        assert state.cursor_position == 5

    def test_set_value(self) -> None:
        """Test setting value."""
        state = PromptInputState()
        state.set_value("New text")
        assert state.value == "New text"
        assert state.cursor_position == 8  # Moved to end

    def test_set_value_preserves_cursor(self) -> None:
        """Test setting value preserves cursor."""
        state = PromptInputState(value="Hello world", cursor_position=5)
        state.set_value("Hi")
        assert state.cursor_position == 2

    def test_move_cursor(self) -> None:
        """Test moving cursor."""
        state = PromptInputState(value="Hello world")
        state.move_cursor(5)
        assert state.cursor_position == 5

    def test_move_cursor_clamp_left(self) -> None:
        """Test cursor clamping at left boundary."""
        state = PromptInputState(value="Hello")
        state.move_cursor(-5)
        assert state.cursor_position == 0

    def test_move_cursor_clamp_right(self) -> None:
        """Test cursor clamping at right boundary."""
        state = PromptInputState(value="Hello")
        state.move_cursor(100)
        assert state.cursor_position == 5

    def test_insert_at_cursor(self) -> None:
        """Test inserting text at cursor."""
        state = PromptInputState(value="Hello world", cursor_position=5)
        state.insert_at_cursor(" there")
        assert state.value == "Hello there world"
        assert state.cursor_position == 11

    def test_delete_at_cursor(self) -> None:
        """Test deleting text at cursor (forward delete)."""
        state = PromptInputState(value="Hello world", cursor_position=5)
        state.delete_at_cursor(3)
        # Deletes ' ' (pos 5), 'w' (pos 6), 'o' (pos 7)
        assert state.value == "Hellorld"

    def test_delete_backward(self) -> None:
        """Test deleting backward from cursor."""
        state = PromptInputState(value="Hello world", cursor_position=7)
        state.delete_backward(3)
        # Deletes 'o', ' ', 'w' (3 chars before position 7)
        assert state.value == "Hellorld"
        assert state.cursor_position == 4

    def test_delete_backward_at_start(self) -> None:
        """Test delete backward at start does nothing."""
        state = PromptInputState(value="Hello", cursor_position=0)
        state.delete_backward(3)
        assert state.value == "Hello"
        assert state.cursor_position == 0

    def test_set_mode(self) -> None:
        """Test setting input mode."""
        state = PromptInputState()
        state.set_mode(PromptInputMode.VIM_INSERT)
        assert state.mode == PromptInputMode.VIM_INSERT

    def test_toggle_multiline(self) -> None:
        """Test toggling multiline."""
        state = PromptInputState()
        assert state.is_multiline is False
        state.toggle_multiline()
        assert state.is_multiline is True

    def test_show_suggestions(self) -> None:
        """Test showing suggestions."""
        state = PromptInputState()
        suggestions = [
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
        ]
        state.display_suggestions(suggestions)
        assert state.show_suggestions is True
        assert len(state.suggestions) == 1

    def test_hide_suggestions(self) -> None:
        """Test hiding suggestions."""
        state = PromptInputState()
        state.display_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
        ])
        state.hide_suggestions()
        assert state.show_suggestions is False
        assert len(state.suggestions) == 0

    def test_navigate_suggestions(self) -> None:
        """Test navigating through suggestions."""
        state = PromptInputState()
        state.display_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/status", description="Show status"),
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/clear", description="Clear screen"),
        ])
        assert state.suggestion_index == 0
        state.next_suggestion()
        assert state.suggestion_index == 1
        state.next_suggestion()
        assert state.suggestion_index == 2
        state.next_suggestion()
        # Wraps around
        assert state.suggestion_index == 0
        state.previous_suggestion()
        assert state.suggestion_index == 2
        state.previous_suggestion()
        assert state.suggestion_index == 1

    def test_select_suggestion(self) -> None:
        """Test selecting a suggestion."""
        state = PromptInputState()
        state.display_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/status", description="Show status"),
        ])
        state.select_suggestion(1)
        # Value is set to selected suggestion text
        assert state.value == "/status"
        assert state.show_suggestions is False

    def test_history_navigation(self) -> None:
        """Test history navigation."""
        state = PromptInputState(history=["cmd1", "cmd2", "cmd3"])
        assert state.history_index == -1
        state.history_up()
        assert state.history_index == 2
        assert state.value == "cmd3"
        state.history_up()
        assert state.history_index == 1
        assert state.value == "cmd2"
        state.history_down()
        assert state.history_index == 2
        state.history_down()
        # At end of history, goes back to current input
        assert state.history_index == -1

    def test_clear(self) -> None:
        """Test clearing input."""
        state = PromptInputState(value="Hello world", cursor_position=5)
        state.clear()
        assert state.value == ""
        assert state.cursor_position == 0


# =============================================================================
# PromptInputFooter Tests
# =============================================================================


class TestPromptInputFooter:
    """Tests for PromptInputFooter."""

    def test_create(self) -> None:
        """Test creating footer."""
        footer = PromptInputFooter()
        assert footer.show_mode_indicator is True
        assert footer.show_queued_commands is False
        assert footer.show_stash_notice is False

    def test_with_queued_commands(self) -> None:
        """Test footer with queued commands."""
        footer = PromptInputFooter(
            queued_commands=["cmd1", "cmd2"],
            show_queued_commands=True,
        )
        assert footer.queued_commands == ["cmd1", "cmd2"]
        assert footer.show_queued_commands is True

    def test_with_stash_notice(self) -> None:
        """Test footer with stash notice."""
        footer = PromptInputFooter(
            stash_notice="Prompt is stashed",
            show_stash_notice=True,
        )
        assert footer.stash_notice == "Prompt is stashed"

    def test_update_mode_indicator(self) -> None:
        """Test updating mode indicator."""
        footer = PromptInputFooter()
        footer.update_mode_indicator(PromptInputMode.VIM_INSERT)
        assert footer.current_mode == PromptInputMode.VIM_INSERT


# =============================================================================
# PromptInput Tests
# =============================================================================


class TestPromptInput:
    """Tests for PromptInput."""

    def test_create(self) -> None:
        """Test creating prompt input."""
        inp = PromptInput()
        assert inp.get_state() is not None
        assert inp.get_state().value == ""
        assert inp.get_state().mode == PromptInputMode.EDIT
        assert inp.get_state().show_suggestions is False

    def test_set_value(self) -> None:
        """Test setting input value."""
        inp = PromptInput()
        inp.set_value("Hello")
        assert inp.get_state().value == "Hello"

    def test_get_value(self) -> None:
        """Test getting input value."""
        inp = PromptInput()
        inp.set_value("world")
        assert inp.get_value() == "world"

    def test_insert_text(self) -> None:
        """Test inserting text."""
        inp = PromptInput()
        inp.set_value("Hello")
        inp.get_state().move_cursor(5)
        inp.insert_text(" world")
        assert inp.get_value() == "Hello world"

    def test_insert_text_in_middle(self) -> None:
        """Test inserting text in middle."""
        inp = PromptInput()
        inp.set_value("Hello world")
        inp.get_state().move_cursor(5)
        inp.insert_text(" there")
        assert inp.get_value() == "Hello there world"

    def test_delete_character_backward(self) -> None:
        """Test deleting character backward."""
        inp = PromptInput()
        inp.set_value("Hello")
        inp.get_state().move_cursor(5)
        inp.delete_backward()
        assert inp.get_value() == "Hell"

    def test_delete_character_forward(self) -> None:
        """Test deleting character forward (backspace in insert mode)."""
        inp = PromptInput()
        inp.set_value("Hello")
        inp.get_state().move_cursor(4)
        inp.delete_forward()
        assert inp.get_value() == "Hell"

    def test_submit(self) -> None:
        """Test submitting input."""
        inp = PromptInput()
        inp.set_value("Hello world")
        submitted: list[str] = []
        inp.set_on_submit(lambda text: submitted.append(text))
        inp.submit()
        assert submitted == ["Hello world"]

    def test_submit_empty(self) -> None:
        """Test submitting empty input."""
        inp = PromptInput()
        submitted: list[str] = []
        inp.set_on_submit(lambda text: submitted.append(text))
        inp.submit()
        # Empty input should not submit
        assert submitted == []

    def test_clear(self) -> None:
        """Test clearing input."""
        inp = PromptInput()
        inp.set_value("Hello world")
        inp.clear()
        assert inp.get_value() == ""
        assert inp.get_state().cursor_position == 0

    def test_set_mode(self) -> None:
        """Test setting input mode."""
        inp = PromptInput()
        inp.set_mode(PromptInputMode.VIM_INSERT)
        assert inp.get_state().mode == PromptInputMode.VIM_INSERT

    def test_vim_normal_mode(self) -> None:
        """Test entering vim normal mode."""
        inp = PromptInput()
        inp.set_mode(PromptInputMode.VIM_INSERT)
        inp.set_value("Hello world")
        inp.get_state().move_cursor(5)
        inp.set_mode(PromptInputMode.VIM_NORMAL)
        # In normal mode, cursor should be on last char
        assert inp.get_state().cursor_position == 10
        assert inp.get_state().mode == PromptInputMode.VIM_NORMAL

    def test_history_with_submit(self) -> None:
        """Test that submitted commands are added to history."""
        inp = PromptInput()
        inp.set_value("cmd1")
        inp.submit()
        inp.set_value("cmd2")
        inp.submit()
        state = inp.get_state()
        assert state.history == ["cmd1", "cmd2"]

    def test_suggestions_filtering(self) -> None:
        """Test filtering suggestions by prefix."""
        inp = PromptInput()
        inp.set_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/status", description="Show status"),
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/clear", description="Clear screen"),
        ])
        filtered = inp.get_suggestions_for_prefix("/he")
        assert len(filtered) == 1
        assert filtered[0].text == "/help"

    def test_suggestions_no_prefix(self) -> None:
        """Test suggestions with empty prefix returns all."""
        inp = PromptInput()
        inp.set_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/status", description="Show status"),
        ])
        filtered = inp.get_suggestions_for_prefix("")
        assert len(filtered) == 2

    def test_show_suggestions(self) -> None:
        """Test showing suggestions."""
        inp = PromptInput()
        inp.set_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
        ])
        inp.show_suggestions()
        state = inp.get_state()
        assert state.show_suggestions is True
        assert len(state.suggestions) == 1

    def test_hide_suggestions(self) -> None:
        """Test hiding suggestions."""
        inp = PromptInput()
        inp.set_suggestions([
            PromptInputSuggestion(type=SuggestionType.COMMAND, text="/help", description="Show help"),
        ])
        inp.show_suggestions()
        inp.hide_suggestions()
        state = inp.get_state()
        assert state.show_suggestions is False

    def test_get_footer(self) -> None:
        """Test getting footer state."""
        inp = PromptInput()
        footer = inp.get_footer()
        assert footer is not None
        assert footer.show_mode_indicator is True

    def test_placeholder(self) -> None:
        """Test placeholder text."""
        inp = PromptInput(placeholder="Enter command...")
        assert inp.placeholder == "Enter command..."
