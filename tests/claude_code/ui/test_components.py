"""Tests for UI shared components (Theme, Store, VirtualScrollResult, etc.)."""

from __future__ import annotations

import pytest

from claude_code.ui.components import (
    Colors,
    DEFAULT_THEME,
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


class TestColors:
    """Tests for Colors enum."""

    def test_values(self) -> None:
        """Colors has expected values."""
        assert Colors.PERMISSION == "#f0b000"
        assert Colors.ERROR == "#f85149"
        assert Colors.SUCCESS == "#3fb950"
        assert Colors.PRIMARY == "#58a6ff"
        assert Colors.INFO == "#8b949e"
        assert Colors.DIM == "#6e7681"
        assert Colors.WARNING == "#d29922"
        assert Colors.TEXT == "#e6edf3"
        assert Colors.TEXT_MUTED == "#8b949e"


class TestTheme:
    """Tests for Theme."""

    def test_default_values(self) -> None:
        """Theme has correct defaults."""
        theme = Theme()
        assert theme.primary == Colors.PRIMARY.value
        assert theme.secondary == Colors.INFO.value
        assert theme.surface == "#0d1117"
        assert theme.surface_darken == "#161b22"

    def test_to_dict(self) -> None:
        """to_dict returns correct structure."""
        theme = Theme()
        d = theme.to_dict()
        assert d["primary"] == Colors.PRIMARY.value
        assert d["surface"] == "#0d1117"
        assert d["text-muted"] == Colors.TEXT_MUTED.value


class TestStore:
    """Tests for Store."""

    def test_initial_state(self) -> None:
        """Store initializes with correct state."""
        store = Store({"count": 0})
        assert store.get_state() == {"count": 0}

    def test_set_state(self) -> None:
        """set_state updates state."""
        store = Store({"count": 0})
        store.set_state(lambda s: {"count": s["count"] + 1})
        assert store.get_state() == {"count": 1}

    def test_set_state_no_change(self) -> None:
        """set_state with no change doesn't notify."""
        store = Store({"count": 0})
        notified = []

        def listener() -> None:
            notified.append(1)

        store.subscribe(listener)
        store.set_state(lambda s: {"count": 0})  # Same value
        assert notified == []

    def test_subscribe_unsubscribe(self) -> None:
        """subscribe and unsubscribe work."""
        store = Store({"count": 0})
        notified = []

        def listener() -> None:
            notified.append(1)

        unsub = store.subscribe(listener)
        store.set_state(lambda s: {"count": 1})
        assert notified == [1]

        unsub()
        store.set_state(lambda s: {"count": 2})
        assert notified == [1]  # Not notified again

    def test_listener_count(self) -> None:
        """__len__ returns listener count."""
        store = Store({"count": 0})
        assert len(store) == 0
        store.subscribe(lambda: None)
        assert len(store) == 1
        store.subscribe(lambda: None)
        assert len(store) == 2

    def test_on_change_callback(self) -> None:
        """on_change callback is called."""
        changes: list[tuple[dict[str, object], dict[str, object]]] = []

        def on_change(next_state: dict[str, object], prev: dict[str, object]) -> None:
            changes.append((next_state, prev))

        store = Store({"count": 0}, on_change=on_change)
        store.set_state(lambda s: {"count": s["count"] + 1})
        assert len(changes) == 1
        assert changes[0][0] == {"count": 1}
        assert changes[0][1] == {"count": 0}

    def test_set_state_non_dict(self) -> None:
        """Store works with non-dict state."""
        store = Store([1, 2, 3])
        store.set_state(lambda s: s + [4])
        assert store.get_state() == [1, 2, 3, 4]


class TestVirtualScrollResult:
    """Tests for VirtualScrollResult."""

    def test_default_constants(self) -> None:
        """Constants have expected values."""
        assert VirtualScrollResult.DEFAULT_ESTIMATE == 3
        assert VirtualScrollResult.OVERSCAN_ROWS == 80
        assert VirtualScrollResult.MAX_MOUNTED_ITEMS == 300
        assert VirtualScrollResult.SLIDE_STEP == 25

    def test_set_items(self) -> None:
        """set_items initializes items and offsets."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])
        assert vs.item_count == 3

    def test_compute_range_empty(self) -> None:
        """compute_range with no items returns (0, 0)."""
        vs = VirtualScrollResult[str]()
        assert vs.compute_range(0, 100) == (0, 0)

    def test_compute_range(self) -> None:
        """compute_range returns visible range with overscan."""
        vs = VirtualScrollResult[str]()
        vs.set_items([str(i) for i in range(100)])
        start, end = vs.compute_range(0, 20)
        assert start >= 0
        assert end > start
        assert end <= start + VirtualScrollResult.MAX_MOUNTED_ITEMS

    def test_measure_item(self) -> None:
        """measure_item caches height and recomputes offsets."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])
        vs.measure_item(0, 10)
        vs.measure_item(1, 5)
        assert vs.get_item_height(0) == 10
        assert vs.get_item_height(1) == 5

    def test_get_item_height_unmeasured(self) -> None:
        """Unmeasured items return default estimate."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b"])
        assert vs.get_item_height(0) == VirtualScrollResult.DEFAULT_ESTIMATE

    def test_get_total_height(self) -> None:
        """get_total_height calculates correctly."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c"])
        # With default estimates, total should be 3 * 3 = 9
        height = vs.get_total_height()
        assert height == 9

    def test_get_total_height_with_measured(self) -> None:
        """get_total_height uses measured heights."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b"])
        vs.measure_item(0, 5)
        vs.measure_item(1, 10)
        # offset[1] = 5, height[1] = 10, total = 5 + 10 = 15
        assert vs.get_total_height() == 15

    def test_scroll_to_index(self) -> None:
        """scroll_to_index returns correct position."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a", "b", "c", "d", "e"])
        pos = vs.scroll_to_index(2)
        assert pos == 6  # 2 * 3 (default estimate)

    def test_scroll_to_index_out_of_range(self) -> None:
        """scroll_to_index with bad index returns 0."""
        vs = VirtualScrollResult[str]()
        vs.set_items(["a"])
        assert vs.scroll_to_index(99) == 0


class TestMessageType:
    """Tests for MessageType enum."""

    def test_values(self) -> None:
        """MessageType has expected values."""
        assert MessageType.USER == "user"
        assert MessageType.ASSISTANT == "assistant"
        assert MessageType.SYSTEM == "system"
        assert MessageType.TOOL_USE == "tool_use"
        assert MessageType.TOOL_RESULT == "tool_result"
        assert MessageType.THINKING == "thinking"


class TestMessageDisplay:
    """Tests for MessageDisplay."""

    def test_creation(self) -> None:
        """MessageDisplay can be created."""
        import time

        msg = MessageDisplay(
            id="msg-1",
            type=MessageType.USER,
            content="Hello",
            timestamp=time.time(),
        )
        assert msg.id == "msg-1"
        assert msg.type == MessageType.USER
        assert msg.content == "Hello"
        assert msg.is_meta is False
        assert msg.is_hidden is False

    def test_from_text(self) -> None:
        """from_text creates a message with default values."""
        msg = MessageDisplay.from_text("Hello, world!")
        assert msg.content == "Hello, world!"
        assert msg.type == MessageType.ASSISTANT
        assert msg.id == ""


class TestDialogStyle:
    """Tests for DialogStyle."""

    def test_creation(self) -> None:
        """DialogStyle has correct defaults."""
        style = DialogStyle()
        assert style.color == Colors.PERMISSION.value
        assert style.hide_border is False
        assert style.hide_input_guide is False


class TestKeyboardShortcut:
    """Tests for KeyboardShortcut."""

    def test_creation(self) -> None:
        """KeyboardShortcut can be created."""
        shortcut = KeyboardShortcut(key="ctrl+c", action="copy")
        assert shortcut.key == "ctrl+c"
        assert shortcut.action == "copy"
        assert shortcut.context is None
        assert shortcut.description is None


class TestScrollState:
    """Tests for ScrollState."""

    def test_default_values(self) -> None:
        """ScrollState has correct defaults."""
        state = ScrollState()
        assert state.position == 0
        assert state.viewport_height == 0
        assert state.max_position == 0
        assert state.sticky_prompt_index == -1

    def test_update_viewport(self) -> None:
        """update_viewport works."""
        state = ScrollState()
        state.update_viewport(height=24, max_pos=100)
        assert state.viewport_height == 24
        assert state.max_position == 100

    def test_scroll_by(self) -> None:
        """scroll_by works correctly."""
        state = ScrollState(max_position=100)
        state.scroll_by(10)
        assert state.position == 10
        state.scroll_by(-5)
        assert state.position == 5

    def test_scroll_by_bounds(self) -> None:
        """scroll_by respects bounds."""
        state = ScrollState(max_position=100)
        state.scroll_by(200)
        assert state.position == 100
        state.scroll_by(-200)
        assert state.position == 0

    def test_scroll_to(self) -> None:
        """scroll_to works correctly."""
        state = ScrollState(max_position=100)
        state.scroll_to(50)
        assert state.position == 50

    def test_scroll_to_bounds(self) -> None:
        """scroll_to respects bounds."""
        state = ScrollState(max_position=100)
        state.scroll_to(200)
        assert state.position == 100
        state.scroll_to(-10)
        assert state.position == 0
