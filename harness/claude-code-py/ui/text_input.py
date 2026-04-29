"""UI text input components for Claude Code TUI.

TypeScript equivalent: TextInput.tsx, BaseTextInput.tsx
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


class InputType(StrEnum):
    """Input field types."""

    TEXT = "text"
    PASSWORD = "password"
    SEARCH = "search"
    EMAIL = "email"
    NUMBER = "number"


# =============================================================================
# Input State
# =============================================================================


@dataclass
class InputState:
    """State for text input.

    Attributes:
        value: Current input value.
        cursor_position: Current cursor position.
        is_valid: Whether input is valid.
        error_message: Error message if invalid.
        is_focused: Whether input has focus.
        is_readonly: Whether input is read-only.
    """

    value: str = ""
    cursor_position: int = 0
    is_valid: bool = True
    error_message: str | None = None
    is_focused: bool = False
    is_readonly: bool = False

    def set_valid(self) -> None:
        """Mark input as valid."""
        self.is_valid = True
        self.error_message = None

    def set_invalid(self, error_message: str) -> None:
        """Mark input as invalid.

        Args:
            error_message: Error description.
        """
        self.is_valid = False
        self.error_message = error_message

    def set_value(self, value: str) -> None:
        """Set input value.

        Args:
            value: New value.
        """
        self.value = value
        self.cursor_position = len(value)


# =============================================================================
# Text Input Highlight
# =============================================================================


@dataclass
class TextInputHighlight:
    """Highlight range in text input.

    Attributes:
        start: Start position.
        end: End position.
    """

    start: int
    end: int

    def contains(self, position: int) -> bool:
        """Check if position is within highlight.

        Args:
            position: Position to check.

        Returns:
            True if within range.
        """
        return self.start <= position <= self.end


# =============================================================================
# Base Text Input
# =============================================================================


@dataclass
class BaseTextInput:
    """Base text input widget.

    TypeScript equivalent: BaseTextInput component.

    Attributes:
        id: Unique identifier.
        input_type: Input type.
        placeholder: Placeholder text.
        max_length: Maximum input length.
        is_readonly: Whether input is read-only.
    """

    id: str = ""
    input_type: InputType = InputType.TEXT
    placeholder: str = ""
    max_length: int | None = None
    is_readonly: bool = False
    _state: InputState = field(default_factory=InputState)
    _highlights: list[TextInputHighlight] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize state after construction."""
        self._state.is_readonly = self.is_readonly

    def get_state(self) -> InputState:
        """Get current state.

        Returns:
            Input state.
        """
        return self._state

    def get_value(self) -> str:
        """Get current value.

        Returns:
            Current input value.
        """
        return self._state.value

    def set_value(self, value: str) -> None:
        """Set input value.

        Args:
            value: New value.
        """
        if self.max_length is not None and len(value) > self.max_length:
            value = value[: self.max_length]
        self._state.value = value
        self._state.cursor_position = len(value)

    def clear(self) -> None:
        """Clear input."""
        self._state.value = ""
        self._state.cursor_position = 0

    def set_error(self, message: str) -> None:
        """Set error state.

        Args:
            message: Error message.
        """
        self._state.set_invalid(message)

    def clear_error(self) -> None:
        """Clear error state."""
        self._state.set_valid()

    def get_masked_value(self) -> str:
        """Get masked value for password fields.

        Returns:
            Masked value if password, else plain value.
        """
        if self.input_type == InputType.PASSWORD:
            return "*" * len(self._state.value)
        return self._state.value

    def add_highlight(self, start: int, end: int) -> None:
        """Add a highlight range.

        Args:
            start: Start position.
            end: End position.
        """
        self._highlights.append(TextInputHighlight(start=start, end=end))

    def get_highlights(self) -> list[TextInputHighlight]:
        """Get all highlights.

        Returns:
            List of highlights.
        """
        return list(self._highlights)

    def clear_highlights(self) -> None:
        """Clear all highlights."""
        self._highlights.clear()

    def focus(self) -> None:
        """Focus the input."""
        self._state.is_focused = True

    def blur(self) -> None:
        """Blur the input."""
        self._state.is_focused = False


# =============================================================================
# Text Input
# =============================================================================


class TextInput(BaseTextInput):
    """Text input widget.

    TypeScript equivalent: TextInput component.

    Attributes:
        is_multiline: Whether multiline input is enabled.
        max_lines: Maximum lines for multiline input.
    """

    def __init__(
        self,
        id: str = "",
        input_type: InputType = InputType.TEXT,
        placeholder: str = "",
        max_length: int | None = None,
        is_readonly: bool = False,
        is_multiline: bool = False,
        max_lines: int | None = None,
    ) -> None:
        """Initialize text input.

        Args:
            id: Unique identifier.
            input_type: Input type.
            placeholder: Placeholder text.
            max_length: Maximum character length.
            is_readonly: Whether read-only.
            is_multiline: Whether multiline enabled.
            max_lines: Maximum lines.
        """
        super().__init__(
            id=id,
            input_type=input_type,
            placeholder=placeholder,
            max_length=max_length,
            is_readonly=is_readonly,
        )
        self.is_multiline = is_multiline
        self.max_lines = max_lines
        self._on_change: Callable[[str], None] | None = None
        self._on_submit: Callable[[str], None] | None = None

    def set_value(self, value: str) -> None:
        """Set input value with multiline enforcement.

        Args:
            value: New value.
        """
        if self.max_length is not None and len(value) > self.max_length:
            value = value[: self.max_length]

        if self.max_lines is not None:
            lines = value.split("\n")
            if len(lines) > self.max_lines:
                lines = lines[: self.max_lines]
                value = "\n".join(lines)

        self._state.value = value
        self._state.cursor_position = len(value)

        if self._on_change:
            self._on_change(value)

    def set_on_change(self, callback: Callable[[str], None]) -> None:
        """Set on_change callback.

        Args:
            callback: Function called when value changes.
        """
        self._on_change = callback

    def set_on_submit(self, callback: Callable[[str], None]) -> None:
        """Set on_submit callback.

        Args:
            callback: Function called on submit.
        """
        self._on_submit = callback

    def submit(self) -> None:
        """Submit the input."""
        if self._on_submit:
            self._on_submit(self._state.value)
