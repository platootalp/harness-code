"""UI prompt input components for Claude Code TUI.

TypeScript equivalent: PromptInput.tsx and sub-components.

Provides the main user input component with:
- Multi-line input support
- Vim mode support
- Slash command suggestions
- History navigation
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class PromptInputMode(StrEnum):
    """Prompt input modes."""

    EDIT = "edit"
    VIM_NORMAL = "vim_normal"
    VIM_INSERT = "vim_insert"
    VIM_VISUAL = "vim_visual"


class VimMode(StrEnum):
    """Vim editing modes."""

    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    COMMAND = "command"


class SuggestionType(StrEnum):
    """Types of input suggestions."""

    COMMAND = "command"
    FILE = "file"
    SEARCH = "search"
    HISTORY = "history"


# =============================================================================
# Suggestion
# =============================================================================


@dataclass
class PromptInputSuggestion:
    """A suggestion in the prompt input.

    Attributes:
        type: Type of suggestion.
        text: The suggestion text.
        description: Human-readable description.
        is_selected: Whether this suggestion is selected.
        score: Match score for fuzzy matching.
    """

    type: SuggestionType
    text: str
    description: str
    is_selected: bool = False
    score: int = 0

    def update_selection(self, selected: bool) -> None:
        """Update selection state.

        Args:
            selected: Whether this suggestion is selected.
        """
        self.is_selected = selected


# =============================================================================
# Prompt Input State
# =============================================================================


@dataclass
class PromptInputState:
    """State for the prompt input.

    Attributes:
        value: Current input text.
        cursor_position: Current cursor position.
        mode: Current input mode.
        show_suggestions: Whether suggestions are shown.
        suggestions: Available suggestions.
        suggestion_index: Currently selected suggestion index.
        history: Command history.
        history_index: Current history navigation index (-1 = no history).
        is_multiline: Whether multiline input is enabled.
    """

    value: str = ""
    cursor_position: int = 0
    mode: PromptInputMode = PromptInputMode.EDIT
    _show_suggestions: bool = field(default=False, repr=False)
    suggestions: list[PromptInputSuggestion] = field(default_factory=list)
    suggestion_index: int = 0
    history: list[str] = field(default_factory=list)
    history_index: int = -1
    is_multiline: bool = False

    @property
    def show_suggestions(self) -> bool:
        """Whether suggestions are shown."""
        return self._show_suggestions

    @show_suggestions.setter
    def show_suggestions(self, value: bool) -> None:
        """Set show suggestions flag."""
        self._show_suggestions = value

    def set_value(self, value: str) -> None:
        """Set input value.

        Args:
            value: New input text.
        """
        self.value = value
        self.cursor_position = len(value)

    def move_cursor(self, position: int) -> None:
        """Move cursor to position.

        Args:
            position: Target cursor position.
        """
        self.cursor_position = max(0, min(len(self.value), position))

    def insert_at_cursor(self, text: str) -> None:
        """Insert text at cursor position.

        Args:
            text: Text to insert.
        """
        before = self.value[: self.cursor_position]
        after = self.value[self.cursor_position :]
        self.value = before + text + after
        self.cursor_position += len(text)

    def delete_at_cursor(self, count: int) -> None:
        """Delete text at cursor (forward delete).

        Args:
            count: Number of characters to delete.
        """
        pos = self.cursor_position
        if pos >= len(self.value):
            return
        delete_count = min(count, len(self.value) - pos)
        self.value = self.value[:pos] + self.value[pos + delete_count :]

    def delete_backward(self, count: int) -> None:
        """Delete text before cursor.

        Args:
            count: Number of characters to delete.
        """
        if self.cursor_position <= 0:
            return
        delete_count = min(count, self.cursor_position)
        new_pos = self.cursor_position - delete_count
        self.value = self.value[:new_pos] + self.value[self.cursor_position :]
        self.cursor_position = new_pos

    def set_mode(self, mode: PromptInputMode) -> None:
        """Set input mode.

        Args:
            mode: New input mode.
        """
        self.mode = mode
        if mode == PromptInputMode.VIM_NORMAL and self.value:
            # In normal mode, cursor goes to end
            self.cursor_position = len(self.value) - 1

    def toggle_multiline(self) -> None:
        """Toggle multiline input mode."""
        self.is_multiline = not self.is_multiline

    def display_suggestions(self, suggestions: list[PromptInputSuggestion]) -> None:
        """Show suggestions list.

        Args:
            suggestions: Suggestions to display.
        """
        self.suggestions = list(suggestions)
        self._show_suggestions = True
        self.suggestion_index = 0

    def show_suggestions_at(
        self, suggestions: list[PromptInputSuggestion]
    ) -> None:
        """Show suggestions list (alias)."""
        self.display_suggestions(suggestions)

    def set_suggestions(self, suggestions: list[PromptInputSuggestion]) -> None:
        """Set suggestions without showing them."""
        self.suggestions = list(suggestions)

    def hide_suggestions(self) -> None:
        """Hide suggestions."""
        self.suggestions = []
        self.show_suggestions = False
        self.suggestion_index = 0

    def next_suggestion(self) -> None:
        """Navigate to next suggestion."""
        if not self.suggestions:
            return
        self.suggestion_index = (self.suggestion_index + 1) % len(self.suggestions)

    def previous_suggestion(self) -> None:
        """Navigate to previous suggestion."""
        if not self.suggestions:
            return
        self.suggestion_index = (self.suggestion_index - 1) % len(self.suggestions)

    def select_suggestion(self, index: int) -> None:
        """Select a suggestion by index.

        Args:
            index: Index of suggestion to select.
        """
        if 0 <= index < len(self.suggestions):
            self.suggestion_index = index
            self.value = self.suggestions[index].text
            self.cursor_position = len(self.value)
        self.hide_suggestions()

    def history_up(self) -> None:
        """Navigate up in history."""
        if not self.history:
            return
        if self.history_index == -1:
            self.history_index = len(self.history) - 1
        elif self.history_index > 0:
            self.history_index -= 1
        self.value = self.history[self.history_index]
        self.cursor_position = len(self.value)

    def history_down(self) -> None:
        """Navigate down in history."""
        if self.history_index == -1:
            return
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = self.history[self.history_index]
        else:
            self.history_index = -1
            self.value = ""
        self.cursor_position = len(self.value)

    def clear(self) -> None:
        """Clear the input."""
        self.value = ""
        self.cursor_position = 0
        self.hide_suggestions()


# =============================================================================
# Prompt Input Footer
# =============================================================================


@dataclass
class PromptInputFooter:
    """Footer for the prompt input.

    TypeScript equivalent: PromptInputFooter.tsx

    Attributes:
        show_mode_indicator: Whether to show vim mode indicator.
        show_queued_commands: Whether to show queued commands.
        show_stash_notice: Whether to show stash notice.
        queued_commands: List of queued commands.
        stash_notice: Stash notice text.
        current_mode: Current input mode.
    """

    show_mode_indicator: bool = True
    show_queued_commands: bool = False
    show_stash_notice: bool = False
    queued_commands: list[str] = field(default_factory=list)
    stash_notice: str = ""
    current_mode: PromptInputMode = PromptInputMode.EDIT

    def update_mode_indicator(self, mode: PromptInputMode) -> None:
        """Update the mode indicator.

        Args:
            mode: New mode.
        """
        self.current_mode = mode


# =============================================================================
# Prompt Input
# =============================================================================


class PromptInput:
    """Main prompt input component.

    TypeScript equivalent: PromptInput.tsx

    Handles user text input with vim mode, suggestions, and history.

    Attributes:
        placeholder: Placeholder text when empty.
    """

    def __init__(
        self,
        placeholder: str = "",
        suggestions: list[PromptInputSuggestion] | None = None,
    ) -> None:
        """Initialize prompt input.

        Args:
            placeholder: Placeholder text.
            suggestions: Initial suggestions list.
        """
        self._state = PromptInputState()
        self._suggestion_list: list[PromptInputSuggestion] = suggestions or []
        self._on_submit: Callable[[str], None] | None = None
        self.placeholder = placeholder

    def get_state(self) -> PromptInputState:
        """Get current state.

        Returns:
            Current input state.
        """
        return self._state

    def get_value(self) -> str:
        """Get current input value.

        Returns:
            Current input text.
        """
        return self._state.value

    def set_value(self, value: str) -> None:
        """Set input value.

        Args:
            value: New input text.
        """
        self._state.set_value(value)

    def insert_text(self, text: str) -> None:
        """Insert text at cursor.

        Args:
            text: Text to insert.
        """
        self._state.insert_at_cursor(text)

    def delete_backward(self) -> None:
        """Delete character before cursor."""
        self._state.delete_backward(1)

    def delete_forward(self) -> None:
        """Delete character after cursor."""
        self._state.delete_at_cursor(1)

    def set_mode(self, mode: PromptInputMode) -> None:
        """Set input mode.

        Args:
            mode: New input mode.
        """
        self._state.set_mode(mode)

    def clear(self) -> None:
        """Clear the input."""
        self._state.clear()

    def submit(self) -> None:
        """Submit the current input."""
        value = self._state.value.strip()
        if not value:
            return
        self._state.history.append(value)
        self._state.clear()
        if self._on_submit:
            self._on_submit(value)

    def set_on_submit(self, callback: Callable[[str], None]) -> None:
        """Set submit callback.

        Args:
            callback: Function called on submit.
        """
        self._on_submit = callback

    def set_suggestions(self, suggestions: list[PromptInputSuggestion]) -> None:
        """Set available suggestions.

        Args:
            suggestions: New suggestions list.
        """
        self._suggestion_list = list(suggestions)

    def get_suggestions_for_prefix(self, prefix: str) -> list[PromptInputSuggestion]:
        """Get suggestions matching a prefix.

        Args:
            prefix: Text prefix to match.

        Returns:
            Filtered suggestions.
        """
        if not prefix:
            return list(self._suggestion_list)
        return [s for s in self._suggestion_list if s.text.startswith(prefix)]

    def show_suggestions(self) -> None:
        """Show suggestions matching current input."""
        prefix = self._state.value
        suggestions = self.get_suggestions_for_prefix(prefix)
        self._state.display_suggestions(suggestions)

    def hide_suggestions(self) -> None:
        """Hide suggestions."""
        self._state.hide_suggestions()

    def get_footer(self) -> PromptInputFooter:
        """Get footer state.

        Returns:
            Footer component state.
        """
        return PromptInputFooter(current_mode=self._state.mode)
