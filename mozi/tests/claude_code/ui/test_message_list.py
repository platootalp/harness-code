"""Tests for UI message list components (VirtualMessageList, MessageRenderer)."""

from __future__ import annotations

import pytest

from claude_code.ui.components import VirtualScrollResult
from claude_code.ui.message_list import (
    MessageRenderResult,
    MessageRenderer,
    MessageRow,
    MessageRowState,
    RenderedMessage,
    VirtualMessageList,
    VirtualMessageListState,
)


class TestVirtualMessageListState:
    """Tests for VirtualMessageListState."""

    def test_default_values(self) -> None:
        """VirtualMessageListState has correct defaults."""
        state = VirtualMessageListState()
        assert state.message_count == 0
        assert state.scroll_position == 0
        assert state.viewport_height == 0
        assert state.sticky_prompt_index == -1
        assert state.visible_start == 0
        assert state.visible_end == 0
        assert state.total_height == 0

    def test_update_scroll(self) -> None:
        """update_scroll works correctly."""
        state = VirtualMessageListState()
        state.update_scroll(scroll_position=100, viewport_height=24)
        assert state.scroll_position == 100
        assert state.viewport_height == 24

    def test_set_sticky_prompt(self) -> None:
        """set_sticky_prompt works correctly."""
        state = VirtualMessageListState()
        state.set_sticky_prompt(5)
        assert state.sticky_prompt_index == 5
        state.set_sticky_prompt(-1)
        assert state.sticky_prompt_index == -1


class TestMessageRowState:
    """Tests for MessageRowState."""

    def test_default_values(self) -> None:
        """MessageRowState has correct defaults."""
        state = MessageRowState(message_id="msg-1")
        assert state.message_id == "msg-1"
        assert state.is_selected is False
        assert state.is_expanded is False
        assert state.height is None
        assert state.offset is None

    def test_update_height(self) -> None:
        """update_height works correctly."""
        state = MessageRowState(message_id="msg-1")
        state.update_height(50)
        assert state.height == 50

    def test_update_offset(self) -> None:
        """update_offset works correctly."""
        state = MessageRowState(message_id="msg-1")
        state.update_offset(100)
        assert state.offset == 100

    def test_toggle_expand(self) -> None:
        """toggle_expand works correctly."""
        state = MessageRowState(message_id="msg-1")
        assert state.is_expanded is False
        state.toggle_expand()
        assert state.is_expanded is True
        state.toggle_expand()
        assert state.is_expanded is False


class TestRenderedMessage:
    """Tests for RenderedMessage."""

    def test_default_values(self) -> None:
        """RenderedMessage has correct defaults."""
        msg = RenderedMessage(message_id="msg-1", lines=10)
        assert msg.message_id == "msg-1"
        assert msg.lines == 10
        assert msg.is_truncated is False
        assert msg.truncated_at is None


class TestMessageRenderResult:
    """Tests for MessageRenderResult."""

    def test_default_values(self) -> None:
        """MessageRenderResult has correct defaults."""
        result = MessageRenderResult(message_id="msg-1", rendered_lines=5)
        assert result.message_id == "msg-1"
        assert result.rendered_lines == 5
        assert result.has_error is False
        assert result.error_message is None

    def test_with_error(self) -> None:
        """Can represent an error."""
        result = MessageRenderResult(
            message_id="msg-1",
            rendered_lines=0,
            has_error=True,
            error_message="Render failed",
        )
        assert result.has_error is True
        assert result.error_message == "Render failed"


class TestMessageRenderer:
    """Tests for MessageRenderer."""

    def test_default_values(self) -> None:
        """MessageRenderer has correct defaults."""
        renderer = MessageRenderer()
        assert renderer.max_width == 80
        assert renderer.truncate_threshold == 1000

    def test_custom_values(self) -> None:
        """Custom values work."""
        renderer = MessageRenderer(max_width=120, truncate_threshold=500)
        assert renderer.max_width == 120
        assert renderer.truncate_threshold == 500

    def test_render_text_empty(self) -> None:
        """Empty text renders correctly."""
        renderer = MessageRenderer()
        result = renderer.render_text("", "msg-1")
        assert result.message_id == "msg-1"
        assert result.rendered_lines == 1
        assert result.has_error is False

    def test_render_text_short_lines(self) -> None:
        """Short lines count correctly."""
        renderer = MessageRenderer(max_width=80)
        result = renderer.render_text("Hello, world!", "msg-1")
        assert result.rendered_lines == 1

    def test_render_text_long_lines(self) -> None:
        """Long lines wrap correctly."""
        renderer = MessageRenderer(max_width=10)
        result = renderer.render_text("Hello world!", "msg-1")
        # "Hello world!" is 12 chars, wraps to 2 lines at width 10
        assert result.rendered_lines == 2

    def test_render_text_multiline(self) -> None:
        """Multiline text counts correctly."""
        renderer = MessageRenderer(max_width=80)
        text = "Line 1\nLine 2\nLine 3"
        result = renderer.render_text(text, "msg-1")
        assert result.rendered_lines == 3

    def test_render_text_multiline_long(self) -> None:
        """Multiline with long lines wraps correctly."""
        renderer = MessageRenderer(max_width=10)
        text = "Short\nThis line is quite long"
        result = renderer.render_text(text, "msg-1")
        # "Short" = 1 line, "This line is quite long" (25 chars) = 3 lines
        assert result.rendered_lines == 4


class TestMessageRow:
    """Tests for MessageRow."""

    def test_creation_with_string_content(self) -> None:
        """MessageRow can be created with string content."""
        row = MessageRow(message_id="msg-1", content="Hello")
        assert row.message_id == "msg-1"
        assert row.content == "Hello"

    def test_creation_with_list_content(self) -> None:
        """MessageRow can be created with list content."""
        content: list[dict[str, object]] = [{"type": "text", "text": "Hello"}]
        row = MessageRow(message_id="msg-1", content=content)
        assert row.content == content

    def test_row_state_auto_created(self) -> None:
        """Row state is auto-created if not provided."""
        row = MessageRow(message_id="msg-1")
        assert row.row_state is not None
        assert row.row_state.message_id == "msg-1"

    def test_row_state_replaced_if_mismatched(self) -> None:
        """Row state is replaced if message_id doesn't match."""
        row = MessageRow(
            message_id="msg-1",
            row_state=MessageRowState(message_id="msg-old"),
        )
        assert row.row_state is not None
        assert row.row_state.message_id == "msg-1"


class TestVirtualMessageList:
    """Tests for VirtualMessageList."""

    def test_initialization(self) -> None:
        """VirtualMessageList initializes correctly."""
        vml = VirtualMessageList()
        assert vml.message_count == 0

    def test_add_message(self) -> None:
        """add_message works correctly."""
        vml = VirtualMessageList()
        vml.add_message("msg-1", lines=10)
        assert vml.message_count == 1

    def test_add_duplicate_message(self) -> None:
        """Duplicate messages are ignored."""
        vml = VirtualMessageList()
        vml.add_message("msg-1", lines=10)
        vml.add_message("msg-1", lines=20)
        assert vml.message_count == 1

    def test_remove_message(self) -> None:
        """remove_message works correctly."""
        vml = VirtualMessageList()
        vml.add_message("msg-1", lines=10)
        vml.add_message("msg-2", lines=5)
        assert vml.message_count == 2
        vml.remove_message("msg-1")
        assert vml.message_count == 1

    def test_remove_nonexistent_message(self) -> None:
        """Removing nonexistent message is safe."""
        vml = VirtualMessageList()
        vml.remove_message("msg-1")
        assert vml.message_count == 0

    def test_update_message_height(self) -> None:
        """update_message_height works correctly."""
        vml = VirtualMessageList()
        vml.add_message("msg-1", lines=10)
        lines = vml.get_message_lines("msg-1")
        assert lines == 10
        vml.update_message_height("msg-1", 20)
        lines = vml.get_message_lines("msg-1")
        assert lines == 20

    def test_update_nonexistent_message_height(self) -> None:
        """Updating nonexistent message is safe."""
        vml = VirtualMessageList()
        vml.update_message_height("msg-1", 20)

    def test_get_message_lines(self) -> None:
        """get_message_lines returns estimated height for unknown."""
        vml = VirtualMessageList()
        lines = vml.get_message_lines("msg-unknown")
        assert lines == VirtualScrollResult.DEFAULT_ESTIMATE

    def test_scroll_to_index(self) -> None:
        """scroll_to_index works correctly."""
        vml = VirtualMessageList()
        for i in range(5):
            vml.add_message(f"msg-{i}", lines=10)
        pos = vml.scroll_to_index(2)
        # Uses default estimate (3 lines per item) until measured
        # offset = 2 * 3 = 6
        assert pos == 6

    def test_compute_visible_range(self) -> None:
        """compute_visible_range works correctly."""
        vml = VirtualMessageList()
        for i in range(10):
            vml.add_message(f"msg-{i}", lines=5)
        start, end = vml.compute_visible_range(viewport_top=0, viewport_height=20)
        # With overscan, range will include items
        assert start >= 0
        assert end > start

    def test_set_sticky_prompt(self) -> None:
        """set_sticky_prompt works correctly."""
        vml = VirtualMessageList()
        state = vml.get_state()
        assert state.sticky_prompt_index == -1
        vml.set_sticky_prompt(5)
        assert state.sticky_prompt_index == 5
        vml.set_sticky_prompt(-1)
        assert state.sticky_prompt_index == -1

    def test_get_total_height(self) -> None:
        """get_total_height works correctly."""
        vml = VirtualMessageList()
        vml.add_message("msg-1", lines=10)
        vml.add_message("msg-2", lines=5)
        # Total should be estimated since items aren't measured
        height = vml.get_total_height()
        assert height >= 0
