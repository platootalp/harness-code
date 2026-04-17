"""Tests for UI prompt input components."""

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


class TestPromptInputMode:
    """Tests for PromptInputMode enum."""

    def test_values(self) -> None:
        """PromptInputMode has expected values."""
        assert PromptInputMode.EDIT == "edit"
        assert PromptInputMode.VIM_NORMAL == "vim_normal"
        assert PromptInputMode.VIM_INSERT == "vim_insert"
        assert PromptInputMode.VIM_VISUAL == "vim_visual"


class TestVimMode:
    """Tests for VimMode enum."""

    def test_values(self) -> None:
        """VimMode has expected values."""
        assert VimMode.NORMAL == "normal"
        assert VimMode.INSERT == "insert"
        assert VimMode.VISUAL == "visual"
        assert VimMode.COMMAND == "command"


class TestSuggestionType:
    """Tests for SuggestionType enum."""

    def test_values(self) -> None:
        """SuggestionType has expected values."""
        assert SuggestionType.COMMAND == "command"
        assert SuggestionType.FILE == "file"
        assert SuggestionType.SEARCH == "search"
        assert SuggestionType.HISTORY == "history"


class TestPromptInputSuggestion:
    """Tests for PromptInputSuggestion."""

    def test_creation(self) -> None:
        """PromptInputSuggestion can be created."""
        suggestion = PromptInputSuggestion(
            type=SuggestionType.COMMAND,
            text="/help",
            description="Show help",
        )
        assert suggestion.type == SuggestionType.COMMAND
        assert suggestion.text == "/help"
        assert suggestion.description == "Show help"
        assert suggestion.is_selected is False
        assert suggestion.score == 0

    def test_update_selection(self) -> None:
        """update_selection works."""
        suggestion = PromptInputSuggestion(
            type=SuggestionType.COMMAND,
            text="/help",
            description="Show help",
        )
        suggestion.update_selection(True)
        assert suggestion.is_selected is True


class TestPromptInputState:
    """Tests for PromptInputState."""

    def test_default_values(self) -> None:
        """PromptInputState has correct defaults."""
        state = PromptInputState()
        assert state.value == ""
        assert state.cursor_position == 0
        assert state.mode == PromptInputMode.EDIT
        assert state.show_suggestions is False
        assert state.suggestions == []
        assert state.suggestion_index == 0
        assert state.history == []
        assert state.history_index == -1
        assert state.is_multiline is False

    def test_set_value(self) -> None:
        """set_value updates value and cursor."""
        state = PromptInputState()
        state.set_value("hello")
        assert state.value == "hello"
        assert state.cursor_position == 5

    def test_move_cursor(self) -> None:
        """move_cursor respects bounds."""
        state = PromptInputState()
        state.set_value("hello")
        state.move_cursor(3)
        assert state.cursor_position == 3
        state.move_cursor(-1)
        assert state.cursor_position == 0
        state.move_cursor(100)
        assert state.cursor_position == 5

    def test_insert_at_cursor(self) -> None:
        """insert_at_cursor works."""
        state = PromptInputState()
        state.set_value("hello")
        state.cursor_position = 2
        state.insert_at_cursor("X")
        assert state.value == "heXllo"
        assert state.cursor_position == 3

    def test_delete_at_cursor(self) -> None:
        """delete_at_cursor works."""
        state = PromptInputState()
        state.set_value("hello")
        state.cursor_position = 2
        state.delete_at_cursor(2)
        assert state.value == "heo"

    def test_delete_at_cursor_end(self) -> None:
        """delete_at_cursor at end does nothing."""
        state = PromptInputState()
        state.set_value("hello")
        state.cursor_position = 5
        state.delete_at_cursor(1)
        assert state.value == "hello"

    def test_delete_backward(self) -> None:
        """delete_backward works."""
        state = PromptInputState()
        state.set_value("hello")
        state.cursor_position = 3
        state.delete_backward(2)
        # Delete 2 chars before cursor (pos 1="e", pos 2="l"): "h" + "lo" = "hlo"
        assert state.value == "hlo"
        assert state.cursor_position == 1

    def test_delete_backward_at_start(self) -> None:
        """delete_backward at start does nothing."""
        state = PromptInputState()
        state.set_value("hello")
        state.cursor_position = 0
        state.delete_backward(2)
        assert state.value == "hello"

    def test_set_mode(self) -> None:
        """set_mode works."""
        state = PromptInputState()
        state.set_mode(PromptInputMode.VIM_INSERT)
        assert state.mode == PromptInputMode.VIM_INSERT

    def test_toggle_multiline(self) -> None:
        """toggle_multiline works."""
        state = PromptInputState()
        assert state.is_multiline is False
        state.toggle_multiline()
        assert state.is_multiline is True

    def test_display_suggestions(self) -> None:
        """display_suggestions works."""
        state = PromptInputState()
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/b", "B"),
        ]
        state.display_suggestions(suggestions)
        assert state.show_suggestions is True
        assert len(state.suggestions) == 2
        assert state.suggestion_index == 0

    def test_hide_suggestions(self) -> None:
        """hide_suggestions works."""
        state = PromptInputState()
        suggestions = [PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A")]
        state.display_suggestions(suggestions)
        state.hide_suggestions()
        assert state.show_suggestions is False
        assert len(state.suggestions) == 0
        assert state.suggestion_index == 0

    def test_next_suggestion(self) -> None:
        """next_suggestion cycles."""
        state = PromptInputState()
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/b", "B"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/c", "C"),
        ]
        state.display_suggestions(suggestions)
        state.next_suggestion()
        assert state.suggestion_index == 1
        state.next_suggestion()
        assert state.suggestion_index == 2
        state.next_suggestion()
        assert state.suggestion_index == 0  # Wraps

    def test_previous_suggestion(self) -> None:
        """previous_suggestion cycles."""
        state = PromptInputState()
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/b", "B"),
        ]
        state.display_suggestions(suggestions)
        state.previous_suggestion()
        assert state.suggestion_index == 1  # Wraps to end
        state.previous_suggestion()
        assert state.suggestion_index == 0

    def test_select_suggestion(self) -> None:
        """select_suggestion sets value and hides."""
        state = PromptInputState()
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/help", "Show help"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/clear", "Clear"),
        ]
        state.display_suggestions(suggestions)
        state.select_suggestion(1)
        assert state.value == "/clear"
        assert state.show_suggestions is False

    def test_select_suggestion_out_of_bounds(self) -> None:
        """select_suggestion with bad index is safe."""
        state = PromptInputState()
        suggestions = [PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A")]
        state.display_suggestions(suggestions)
        state.select_suggestion(99)
        assert state.show_suggestions is False

    def test_history_up(self) -> None:
        """history_up navigates correctly."""
        state = PromptInputState()
        state.history = ["cmd1", "cmd2", "cmd3"]
        state.history_up()
        assert state.history_index == 2
        assert state.value == "cmd3"
        state.history_up()
        assert state.history_index == 1
        assert state.value == "cmd2"

    def test_history_up_empty(self) -> None:
        """history_up with no history is safe."""
        state = PromptInputState()
        state.history_up()
        assert state.history_index == -1
        assert state.value == ""

    def test_history_down(self) -> None:
        """history_down navigates correctly."""
        state = PromptInputState()
        state.history = ["cmd1", "cmd2", "cmd3"]
        state.history_index = 2
        state.history_down()
        assert state.history_index == -1
        assert state.value == ""
        state.history_index = 2
        state.value = "temp"
        state.history_down()
        assert state.history_index == -1

    def test_clear(self) -> None:
        """clear works correctly."""
        state = PromptInputState()
        state.set_value("hello")
        suggestions = [PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A")]
        state.display_suggestions(suggestions)
        state.clear()
        assert state.value == ""
        assert state.cursor_position == 0
        assert state.show_suggestions is False


class TestPromptInputFooter:
    """Tests for PromptInputFooter."""

    def test_default_values(self) -> None:
        """PromptInputFooter has correct defaults."""
        footer = PromptInputFooter()
        assert footer.show_mode_indicator is True
        assert footer.show_queued_commands is False
        assert footer.show_stash_notice is False
        assert footer.queued_commands == []
        assert footer.stash_notice == ""
        assert footer.current_mode == PromptInputMode.EDIT

    def test_update_mode_indicator(self) -> None:
        """update_mode_indicator works."""
        footer = PromptInputFooter()
        footer.update_mode_indicator(PromptInputMode.VIM_NORMAL)
        assert footer.current_mode == PromptInputMode.VIM_NORMAL


class TestPromptInput:
    """Tests for PromptInput."""

    def test_creation(self) -> None:
        """PromptInput can be created."""
        inp = PromptInput(placeholder="Type here...")
        assert inp.placeholder == "Type here..."
        assert inp.get_value() == ""

    def test_get_set_value(self) -> None:
        """get_value and set_value work."""
        inp = PromptInput()
        inp.set_value("hello")
        assert inp.get_value() == "hello"

    def test_insert_text(self) -> None:
        """insert_text works."""
        inp = PromptInput()
        inp.set_value("hello")
        state = inp.get_state()
        state.cursor_position = 2
        inp.insert_text("X")
        assert inp.get_value() == "heXllo"

    def test_delete_backward(self) -> None:
        """delete_backward works."""
        inp = PromptInput()
        inp.set_value("hello")
        state = inp.get_state()
        state.cursor_position = 3
        inp.delete_backward()
        assert inp.get_value() == "helo"

    def test_delete_forward(self) -> None:
        """delete_forward works."""
        inp = PromptInput()
        inp.set_value("hello")
        state = inp.get_state()
        state.cursor_position = 2
        inp.delete_forward()
        assert inp.get_value() == "helo"

    def test_set_mode(self) -> None:
        """set_mode works."""
        inp = PromptInput()
        inp.set_mode(PromptInputMode.VIM_INSERT)
        assert inp.get_state().mode == PromptInputMode.VIM_INSERT

    def test_clear(self) -> None:
        """clear works."""
        inp = PromptInput()
        inp.set_value("hello")
        inp.clear()
        assert inp.get_value() == ""

    def test_submit_empty(self) -> None:
        """submit with empty value does nothing."""
        inp = PromptInput()
        called: list[str] = []
        inp.set_on_submit(lambda v: called.append(v))
        inp.submit()
        assert called == []

    def test_submit_adds_to_history(self) -> None:
        """submit adds value to history."""
        inp = PromptInput()
        inp.set_value("hello")
        inp.submit()
        assert inp.get_state().history == ["hello"]
        assert inp.get_value() == ""

    def test_submit_callback(self) -> None:
        """submit calls callback."""
        inp = PromptInput()
        called: list[str] = []
        inp.set_on_submit(lambda v: called.append(v))
        inp.set_value("test")
        inp.submit()
        assert called == ["test"]

    def test_set_suggestions(self) -> None:
        """set_suggestions works."""
        inp = PromptInput()
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/b", "B"),
        ]
        inp.set_suggestions(suggestions)
        filtered = inp.get_suggestions_for_prefix("/a")
        assert len(filtered) == 1
        assert filtered[0].text == "/a"

    def test_get_suggestions_for_prefix_empty(self) -> None:
        """Empty prefix returns all suggestions."""
        inp = PromptInput()
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/b", "B"),
        ]
        inp.set_suggestions(suggestions)
        all_suggestions = inp.get_suggestions_for_prefix("")
        assert len(all_suggestions) == 2

    def test_show_suggestions(self) -> None:
        """show_suggestions filters by current value."""
        inp = PromptInput()
        inp.set_value("/h")
        suggestions = [
            PromptInputSuggestion(SuggestionType.COMMAND, "/help", "Show help"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/hello", "Say hello"),
            PromptInputSuggestion(SuggestionType.COMMAND, "/clear", "Clear"),
        ]
        inp.set_suggestions(suggestions)
        inp.show_suggestions()
        state = inp.get_state()
        assert state.show_suggestions is True
        assert len(state.suggestions) == 2

    def test_hide_suggestions(self) -> None:
        """hide_suggestions works."""
        inp = PromptInput()
        inp.set_suggestions([PromptInputSuggestion(SuggestionType.COMMAND, "/a", "A")])
        inp.show_suggestions()
        inp.hide_suggestions()
        assert inp.get_state().show_suggestions is False

    def test_get_footer(self) -> None:
        """get_footer returns footer state."""
        inp = PromptInput()
        footer = inp.get_footer()
        assert footer.current_mode == PromptInputMode.EDIT
