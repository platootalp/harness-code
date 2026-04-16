"""
Tests for UI text input components.
"""

from __future__ import annotations

import pytest

from claude_code.ui.text_input import (
    BaseTextInput,
    InputState,
    InputType,
    TextInput,
    TextInputHighlight,
)


# =============================================================================
# InputType Tests
# =============================================================================


class TestInputType:
    """Tests for InputType enum."""

    def test_values(self) -> None:
        """Test input type values."""
        assert InputType.TEXT.value == "text"
        assert InputType.PASSWORD.value == "password"
        assert InputType.SEARCH.value == "search"
        assert InputType.EMAIL.value == "email"
        assert InputType.NUMBER.value == "number"


# =============================================================================
# InputState Tests
# =============================================================================


class TestInputState:
    """Tests for InputState."""

    def test_create(self) -> None:
        """Test creating input state."""
        state = InputState()
        assert state.value == ""
        assert state.cursor_position == 0
        assert state.is_valid is True
        assert state.error_message is None
        assert state.is_focused is False
        assert state.is_readonly is False

    def test_with_value(self) -> None:
        """Test state with initial value."""
        state = InputState(value="test", cursor_position=4)
        assert state.value == "test"
        assert state.cursor_position == 4

    def test_set_valid(self) -> None:
        """Test setting validity."""
        state = InputState()
        state.set_valid()
        assert state.is_valid is True
        assert state.error_message is None

    def test_set_invalid(self) -> None:
        """Test setting invalid with message."""
        state = InputState()
        state.set_invalid("Email is required")
        assert state.is_valid is False
        assert state.error_message == "Email is required"

    def test_set_value(self) -> None:
        """Test setting value."""
        state = InputState()
        state.set_value("hello")
        assert state.value == "hello"
        assert state.cursor_position == 5


# =============================================================================
# TextInputHighlight Tests
# =============================================================================


class TestTextInputHighlight:
    """Tests for TextInputHighlight."""

    def test_create(self) -> None:
        """Test creating highlight."""
        h = TextInputHighlight(start=0, end=5)
        assert h.start == 0
        assert h.end == 5

    def test_contains(self) -> None:
        """Test highlight containment."""
        h = TextInputHighlight(start=0, end=5)
        assert h.contains(2) is True
        assert h.contains(5) is True
        assert h.contains(6) is False


# =============================================================================
# BaseTextInput Tests
# =============================================================================


class TestBaseTextInput:
    """Tests for BaseTextInput."""

    def test_create(self) -> None:
        """Test creating base text input."""
        inp = BaseTextInput(id="input-1")
        assert inp.id == "input-1"
        state = inp.get_state()
        assert state.value == ""
        assert state.is_valid is True
        assert inp.input_type == InputType.TEXT

    def test_create_with_type(self) -> None:
        """Test creating with input type."""
        inp = BaseTextInput(id="password", input_type=InputType.PASSWORD)
        assert inp.input_type == InputType.PASSWORD

    def test_create_with_placeholder(self) -> None:
        """Test creating with placeholder."""
        inp = BaseTextInput(id="search", placeholder="Search...")
        assert inp.placeholder == "Search..."

    def test_create_with_max_length(self) -> None:
        """Test creating with max length."""
        inp = BaseTextInput(id="name", max_length=50)
        assert inp.max_length == 50

    def test_create_readonly(self) -> None:
        """Test creating readonly input."""
        inp = BaseTextInput(id="label", is_readonly=True)
        assert inp.is_readonly is True

    def test_set_value(self) -> None:
        """Test setting value."""
        inp = BaseTextInput(id="input")
        inp.set_value("Hello")
        assert inp.get_state().value == "Hello"

    def test_get_value(self) -> None:
        """Test getting value."""
        inp = BaseTextInput(id="input")
        inp.set_value("World")
        assert inp.get_value() == "World"

    def test_max_length_enforcement(self) -> None:
        """Test max length is enforced."""
        inp = BaseTextInput(id="short", max_length=3)
        inp.set_value("Hello world")
        assert inp.get_value() == "Hel"

    def test_clear(self) -> None:
        """Test clearing input."""
        inp = BaseTextInput(id="input")
        inp.set_value("Hello")
        inp.clear()
        assert inp.get_value() == ""
        assert inp.get_state().cursor_position == 0

    def test_set_error(self) -> None:
        """Test setting error state."""
        inp = BaseTextInput(id="input")
        inp.set_error("Invalid email")
        state = inp.get_state()
        assert state.is_valid is False
        assert state.error_message == "Invalid email"

    def test_clear_error(self) -> None:
        """Test clearing error."""
        inp = BaseTextInput(id="input")
        inp.set_error("Error")
        inp.clear_error()
        state = inp.get_state()
        assert state.is_valid is True
        assert state.error_message is None

    def test_password_masking(self) -> None:
        """Test password input masking."""
        inp = BaseTextInput(id="pass", input_type=InputType.PASSWORD)
        inp.set_value("secret")
        masked = inp.get_masked_value()
        assert masked == "******"
        assert masked != "secret"

    def test_text_not_masked(self) -> None:
        """Test text input is not masked."""
        inp = BaseTextInput(id="text", input_type=InputType.TEXT)
        inp.set_value("Hello")
        assert inp.get_masked_value() == "Hello"

    def test_add_highlight(self) -> None:
        """Test adding highlights."""
        inp = BaseTextInput(id="input")
        inp.add_highlight(0, 5)
        highlights = inp.get_highlights()
        assert len(highlights) == 1
        assert highlights[0].start == 0
        assert highlights[0].end == 5

    def test_clear_highlights(self) -> None:
        """Test clearing highlights."""
        inp = BaseTextInput(id="input")
        inp.add_highlight(0, 5)
        inp.add_highlight(10, 15)
        inp.clear_highlights()
        assert len(inp.get_highlights()) == 0

    def test_focus_blur(self) -> None:
        """Test focus and blur."""
        inp = BaseTextInput(id="input")
        inp.focus()
        assert inp.get_state().is_focused is True
        inp.blur()
        assert inp.get_state().is_focused is False

    def test_readonly_input(self) -> None:
        """Test readonly state."""
        inp = BaseTextInput(id="input", is_readonly=True)
        assert inp.get_state().is_readonly is True


# =============================================================================
# TextInput Tests
# =============================================================================


class TestTextInput:
    """Tests for TextInput."""

    def test_create(self) -> None:
        """Test creating text input."""
        inp = TextInput(id="input-1")
        assert inp.id == "input-1"
        assert inp.is_multiline is False
        assert inp.max_lines is None

    def test_create_multiline(self) -> None:
        """Test creating multiline input."""
        inp = TextInput(id="textarea", is_multiline=True, max_lines=10)
        assert inp.is_multiline is True
        assert inp.max_lines == 10

    def test_set_value(self) -> None:
        """Test setting value."""
        inp = TextInput(id="input")
        inp.set_value("Hello world")
        assert inp.get_value() == "Hello world"

    def test_get_value(self) -> None:
        """Test getting value."""
        inp = TextInput(id="input")
        inp.set_value("test")
        assert inp.get_value() == "test"

    def test_multiline_with_newlines(self) -> None:
        """Test multiline input with newlines."""
        inp = TextInput(id="textarea", is_multiline=True)
        inp.set_value("Line 1\nLine 2\nLine 3")
        assert "\n" in inp.get_value()

    def test_max_lines_enforcement(self) -> None:
        """Test max lines enforcement."""
        inp = TextInput(id="limited", is_multiline=True, max_lines=3)
        inp.set_value("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        lines = inp.get_value().split("\n")
        assert len(lines) <= 3

    def test_on_change_callback(self) -> None:
        """Test on_change callback."""
        inp = TextInput(id="input")
        changes: list[str] = []

        def on_change(value: str) -> None:
            changes.append(value)

        inp.set_on_change(on_change)
        inp.set_value("changed")
        assert changes == ["changed"]

    def test_on_submit_callback(self) -> None:
        """Test on_submit callback."""
        inp = TextInput(id="input")
        submits: list[str] = []

        def on_submit(value: str) -> None:
            submits.append(value)

        inp.set_on_submit(on_submit)
        inp.submit()
        assert submits == [""]

    def test_submit_nonempty(self) -> None:
        """Test submit with non-empty value."""
        inp = TextInput(id="input")
        submits: list[str] = []

        def on_submit(value: str) -> None:
            submits.append(value)

        inp.set_on_submit(on_submit)
        inp.set_value("command")
        inp.submit()
        assert submits == ["command"]

    def test_clear(self) -> None:
        """Test clearing input."""
        inp = TextInput(id="input")
        inp.set_value("Hello")
        inp.clear()
        assert inp.get_value() == ""

    def test_password_input(self) -> None:
        """Test password input type."""
        inp = TextInput(id="pass", input_type=InputType.PASSWORD)
        inp.set_value("secret123")
        assert inp.get_masked_value() == "*********"
        assert inp.get_value() == "secret123"
