"""
Tests for ui/components.py - UI components, theme, and state management.
"""

from __future__ import annotations

from typing import Any
import pytest
from claude_code.ui.components import (
    Colors,
    DialogStyle,
    KeyboardShortcut,
    MessageDisplay,
    MessageType,
    PromptInputMode,
    ScrollState,
    Store,
    Theme,
    VirtualScrollResult,
)

# =============================================================================
# Colors Tests
# =============================================================================


class TestColors:
    """Tests for Colors enum."""

    def test_permission_color(self) -> None:
        """Test permission color value."""
        assert Colors.PERMISSION.value == "#f0b000"

    def test_error_color(self) -> None:
        """Test error color value."""
        assert Colors.ERROR.value == "#f85149"

    def test_success_color(self) -> None:
        """Test success color value."""
        assert Colors.SUCCESS.value == "#3fb950"

    def test_primary_color(self) -> None:
        """Test primary color value."""
        assert Colors.PRIMARY.value == "#58a6ff"


# =============================================================================
# Theme Tests
# =============================================================================


class TestTheme:
    """Tests for Theme dataclass."""

    def test_default_values(self) -> None:
        """Test default theme values."""
        theme = Theme()
        assert theme.primary == Colors.PRIMARY.value
        assert theme.error == Colors.ERROR.value
        assert theme.success == Colors.SUCCESS.value
        assert theme.surface == "#0d1117"

    def test_custom_values(self) -> None:
        """Test theme with custom values."""
        theme = Theme(
            primary="#ff0000",
            error="#00ff00",
            surface="#ffffff",
        )
        assert theme.primary == "#ff0000"
        assert theme.error == "#00ff00"
        assert theme.surface == "#ffffff"

    def test_to_dict(self) -> None:
        """Test converting theme to dict."""
        theme = Theme()
        d = theme.to_dict()
        assert "primary" in d
        assert "error" in d
        assert "surface" in d
        assert "text-muted" in d


# =============================================================================
# Store Tests
# =============================================================================


class TestStore:
    """Tests for Store class."""

    def test_initial_state(self) -> None:
        """Test store initial state."""
        store = Store({"count": 0})
        assert store.get_state() == {"count": 0}

    def test_set_state(self) -> None:
        """Test updating state."""
        store = Store({"count": 0})
        store.set_state(lambda s: {"count": s["count"] + 1})
        assert store.get_state() == {"count": 1}

    def test_no_change_returns_early(self) -> None:
        """Test that unchanged state doesn't notify."""
        store = Store({"count": 0})
        notified = []

        def listener() -> None:
            notified.append(True)

        store.subscribe(listener)
        store.set_state(lambda s: {"count": 0})  # Same value
        assert notified == []

    def test_subscribe(self) -> None:
        """Test subscribing to state changes."""
        store = Store({"count": 0})
        notified = []

        def listener() -> None:
            notified.append(store.get_state()["count"])

        store.subscribe(listener)
        store.set_state(lambda s: {"count": 1})
        assert notified == [1]

        store.set_state(lambda s: {"count": 2})
        assert notified == [1, 2]

    def test_unsubscribe(self) -> None:
        """Test unsubscribing from state changes."""
        store = Store({"count": 0})
        notified = []

        def listener() -> None:
            notified.append(1)

        unsubscribe = store.subscribe(listener)
        unsubscribe()
        store.set_state(lambda s: {"count": 1})
        assert notified == []

    def test_on_change_callback(self) -> None:
        """Test on_change callback."""
        changes = []

        def on_change(new_state: Any, old_state: Any) -> None:
            changes.append({"new_state": new_state, "old_state": old_state})

        store = Store({"count": 0}, on_change=on_change)
        store.set_state(lambda s: {"count": 1})

        assert len(changes) == 1
        assert changes[0]["new_state"] == {"count": 1}
        assert changes[0]["old_state"] == {"count": 0}

    def test_multiple_listeners(self) -> None:
        """Test multiple listeners."""
        store = Store({"count": 0})
        results: list[list[int]] = [[], []]

        store.subscribe(lambda: results[0].append(1))
        store.subscribe(lambda: results[1].append(1))

        store.set_state(lambda s: {"count": 1})

        assert results[0] == [1]
        assert results[1] == [1]


# =============================================================================
# VirtualScrollResult Tests
# =============================================================================


class TestVirtualScrollResult:
    """Tests for VirtualScrollResult."""

    def test_set_items(self) -> None:
        """Test setting items."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])
        assert vs.item_count == 3

    def test_default_estimate(self) -> None:
        """Test default height estimate."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])
        assert vs.get_item_height(0) == 3
        assert vs.get_item_height(1) == 3

    def test_measure_item(self) -> None:
        """Test measuring item height."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])

        vs.measure_item(1, 10)
        assert vs.get_item_height(1) == 10
        assert vs.get_item_height(0) == 3  # Unchanged

    def test_compute_range_basic(self) -> None:
        """Test computing visible range."""
        vs = VirtualScrollResult[str]()
        vs.set_items([str(i) for i in range(100)])

        start, end = vs.compute_range(0, 20)
        assert start == 0
        assert end > 0

    def test_compute_range_with_overscan(self) -> None:
        """Test overscan in range computation."""
        vs = VirtualScrollResult[str]()
        vs.set_items([str(i) for i in range(100)])

        # At position 50, should include overscan above
        start, end = vs.compute_range(50, 20)
        assert start < 50  # Should include items above

    def test_total_height(self) -> None:
        """Test total height calculation."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])

        total = vs.get_total_height()
        assert total == 9  # 3 items * 3 rows each

    def test_scroll_to_index(self) -> None:
        """Test scroll position for index."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])

        assert vs.scroll_to_index(0) == 0
        assert vs.scroll_to_index(1) == 3
        assert vs.scroll_to_index(2) == 6

    def test_max_mounted_items(self) -> None:
        """Test max mounted items cap."""
        vs = VirtualScrollResult[str]()
        vs.set_items([str(i) for i in range(1000)])

        # Should cap at MAX_MOUNTED_ITEMS
        start, end = vs.compute_range(0, 20)
        assert end - start <= vs.MAX_MOUNTED_ITEMS


# =============================================================================
# MessageType Tests
# =============================================================================


class TestMessageType:
    """Tests for MessageType enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert MessageType.USER.value == "user"
        assert MessageType.ASSISTANT.value == "assistant"
        assert MessageType.SYSTEM.value == "system"
        assert MessageType.TOOL_USE.value == "tool_use"
        assert MessageType.THINKING.value == "thinking"


# =============================================================================
# MessageDisplay Tests
# =============================================================================


class TestMessageDisplay:
    """Tests for MessageDisplay dataclass."""

    def test_create(self) -> None:
        """Test creating message display."""
        import time

        msg = MessageDisplay(
            id="msg-1",
            type=MessageType.ASSISTANT,
            content="Hello",
            timestamp=time.time(),
        )
        assert msg.type == MessageType.ASSISTANT
        assert msg.is_meta is False
        assert msg.is_hidden is False

    def test_from_text(self) -> None:
        """Test creating from text."""
        msg = MessageDisplay.from_text("Hello")
        assert msg.content == "Hello"
        assert msg.type == MessageType.ASSISTANT

    def test_is_hidden_default(self) -> None:
        """Test is_hidden default."""
        msg = MessageDisplay(
            id="msg-1",
            type=MessageType.SYSTEM,
            content="Meta info",
            timestamp=0.0,
            is_meta=True,
        )
        assert msg.is_hidden is False


# =============================================================================
# DialogStyle Tests
# =============================================================================


class TestDialogStyle:
    """Tests for DialogStyle dataclass."""

    def test_default_values(self) -> None:
        """Test default dialog style."""
        style = DialogStyle()
        assert style.color == Colors.PERMISSION.value
        assert style.hide_border is False
        assert style.hide_input_guide is False


# =============================================================================
# KeyboardShortcut Tests
# =============================================================================


class TestKeyboardShortcut:
    """Tests for KeyboardShortcut dataclass."""

    def test_create(self) -> None:
        """Test creating shortcut."""
        shortcut = KeyboardShortcut(
            key="enter",
            action="confirm",
            context="dialogs",
            description="Confirm action",
        )
        assert shortcut.key == "enter"
        assert shortcut.action == "confirm"
        assert shortcut.context == "dialogs"
        assert shortcut.description == "Confirm action"

    def test_minimal(self) -> None:
        """Test minimal shortcut."""
        shortcut = KeyboardShortcut(key="escape", action="cancel")
        assert shortcut.context is None
        assert shortcut.description is None


# =============================================================================
# ScrollState Tests
# =============================================================================


class TestScrollState:
    """Tests for ScrollState dataclass."""

    def test_initial(self) -> None:
        """Test initial scroll state."""
        state = ScrollState()
        assert state.position == 0
        assert state.viewport_height == 0
        assert state.max_position == 0
        assert state.sticky_prompt_index == -1

    def test_update_viewport(self) -> None:
        """Test updating viewport dimensions."""
        state = ScrollState()
        state.update_viewport(50, 100)
        assert state.viewport_height == 50
        assert state.max_position == 100

    def test_scroll_by(self) -> None:
        """Test scrolling by delta."""
        state = ScrollState(max_position=100)
        state.scroll_by(10)
        assert state.position == 10

    def test_scroll_by_clamp(self) -> None:
        """Test scroll clamping."""
        state = ScrollState(max_position=50)
        state.scroll_by(-10)
        assert state.position == 0
        state.scroll_by(100)
        assert state.position == 50

    def test_scroll_to(self) -> None:
        """Test scrolling to position."""
        state = ScrollState(max_position=100)
        state.scroll_to(50)
        assert state.position == 50

    def test_scroll_to_clamp(self) -> None:
        """Test scroll_to clamping."""
        state = ScrollState(max_position=100)
        state.scroll_to(-5)
        assert state.position == 0
        state.scroll_to(200)
        assert state.position == 100


# =============================================================================
# PromptInputMode Tests
# =============================================================================


class TestPromptInputMode:
    """Tests for PromptInputMode enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert PromptInputMode.EDIT.value == "edit"
        assert PromptInputMode.VIM_NORMAL.value == "vim_normal"
        assert PromptInputMode.VIM_INSERT.value == "vim_insert"
        assert PromptInputMode.VIM_VISUAL.value == "vim_visual"
