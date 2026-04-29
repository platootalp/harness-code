"""Tests for UI text input components (BaseTextInput, TextInput)."""

from __future__ import annotations

import pytest

from claude_code.ui.text_input import (
    BaseTextInput,
    InputState,
    InputType,
    TextInput,
    TextInputHighlight,
)


class TestInputState:
    """Tests for InputState."""

    def test_default_values(self) -> None:
        """InputState has correct defaults."""
        state = InputState()
        assert state.value == ""
        assert state.cursor_position == 0
        assert state.is_valid is True
        assert state.error_message is None
        assert state.is_focused is False
        assert state.is_readonly is False

    def test_set_valid(self) -> None:
        """set_valid clears error state."""
        state = InputState()
        state.set_invalid("Some error")
        assert state.is_valid is False
        state.set_valid()
        assert state.is_valid is True
        assert state.error_message is None

    def test_set_invalid(self) -> None:
        """set_invalid sets error state."""
        state = InputState()
        state.set_invalid("Required field")
        assert state.is_valid is False
        assert state.error_message == "Required field"

    def test_set_value(self) -> None:
        """set_value updates value and cursor."""
        state = InputState()
        state.set_value("hello")
        assert state.value == "hello"
        assert state.cursor_position == 5


class TestTextInputHighlight:
    """Tests for TextInputHighlight."""

    def test_contains(self) -> None:
        """contains works correctly."""
        highlight = TextInputHighlight(start=2, end=5)
        assert highlight.contains(0) is False
        assert highlight.contains(1) is False
        assert highlight.contains(2) is True
        assert highlight.contains(3) is True
        assert highlight.contains(5) is True
        assert highlight.contains(6) is False


class TestBaseTextInput:
    """Tests for BaseTextInput."""

    def test_default_values(self) -> None:
        """BaseTextInput has correct defaults."""
        inp = BaseTextInput()
        assert inp.id == ""
        assert inp.input_type == InputType.TEXT
        assert inp.placeholder == ""
        assert inp.max_length is None
        assert inp.is_readonly is False

    def test_get_set_value(self) -> None:
        """Get and set value work."""
        inp = BaseTextInput()
        inp.set_value("test")
        assert inp.get_value() == "test"

    def test_max_length_enforcement(self) -> None:
        """max_length is enforced on set_value."""
        inp = BaseTextInput(max_length=5)
        inp.set_value("hello world")
        assert inp.get_value() == "hello"

    def test_clear(self) -> None:
        """clear resets value and cursor."""
        inp = BaseTextInput()
        inp.set_value("hello")
        inp.clear()
        assert inp.get_value() == ""
        assert inp.get_state().cursor_position == 0

    def test_set_error(self) -> None:
        """set_error marks input as invalid."""
        inp = BaseTextInput()
        inp.set_error("Invalid email")
        assert inp.get_state().is_valid is False
        assert inp.get_state().error_message == "Invalid email"

    def test_clear_error(self) -> None:
        """clear_error marks input as valid."""
        inp = BaseTextInput()
        inp.set_error("Error")
        inp.clear_error()
        assert inp.get_state().is_valid is True
        assert inp.get_state().error_message is None

    def test_get_masked_value_password(self) -> None:
        """Password fields return masked value."""
        inp = BaseTextInput(input_type=InputType.PASSWORD)
        inp.set_value("secret123")
        assert inp.get_masked_value() == "*********"

    def test_get_masked_value_text(self) -> None:
        """Text fields return plain value."""
        inp = BaseTextInput(input_type=InputType.TEXT)
        inp.set_value("hello")
        assert inp.get_masked_value() == "hello"

    def test_highlights(self) -> None:
        """Highlights can be added and cleared."""
        inp = BaseTextInput()
        inp.add_highlight(0, 5)
        inp.add_highlight(10, 15)
        highlights = inp.get_highlights()
        assert len(highlights) == 2
        inp.clear_highlights()
        assert len(inp.get_highlights()) == 0

    def test_focus_blur(self) -> None:
        """Focus and blur work."""
        inp = BaseTextInput()
        inp.focus()
        assert inp.get_state().is_focused is True
        inp.blur()
        assert inp.get_state().is_focused is False

    def test_readonly_initialization(self) -> None:
        """is_readonly is propagated to state."""
        inp = BaseTextInput(is_readonly=True)
        assert inp.get_state().is_readonly is True


class TestTextInput:
    """Tests for TextInput."""

    def test_default_values(self) -> None:
        """TextInput has correct defaults."""
        inp = TextInput()
        assert inp.is_multiline is False
        assert inp.max_lines is None

    def test_multiline(self) -> None:
        """Multiline can be enabled."""
        inp = TextInput(is_multiline=True, max_lines=10)
        assert inp.is_multiline is True
        assert inp.max_lines == 10

    def test_max_lines_enforcement(self) -> None:
        """max_lines is enforced on set_value."""
        inp = TextInput(is_multiline=True, max_lines=2)
        inp.set_value("line1\nline2\nline3")
        assert inp.get_value() == "line1\nline2"

    def test_on_change_callback(self) -> None:
        """on_change callback is called on set_value."""
        called: list[str] = []

        def on_change(value: str) -> None:
            called.append(value)

        inp = TextInput()
        inp.set_on_change(on_change)
        inp.set_value("test")
        assert called == ["test"]

    def test_on_submit_callback(self) -> None:
        """on_submit callback is called on submit."""
        called: list[str] = []

        def on_submit(value: str) -> None:
            called.append(value)

        inp = TextInput()
        inp.set_on_submit(on_submit)
        inp.set_value("hello")
        inp.submit()
        assert called == ["hello"]

    def test_submit_empty_value(self) -> None:
        """submit with empty value calls callback with empty string."""
        called: list[str] = []

        def on_submit(value: str) -> None:
            called.append(value)

        inp = TextInput()
        inp.set_on_submit(on_submit)
        inp.set_value("")
        inp.submit()
        # TextInput.submit() calls callback regardless of empty value
        assert called == [""]

    def test_submit_whitespace_value(self) -> None:
        """submit with whitespace-only value calls callback."""
        called: list[str] = []

        def on_submit(value: str) -> None:
            called.append(value)

        inp = TextInput()
        inp.set_on_submit(on_submit)
        inp.set_value("   ")
        inp.submit()
        # TextInput.submit() calls callback regardless of whitespace
        assert called == ["   "]
