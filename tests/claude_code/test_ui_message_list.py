"""
Tests for UI message list components.
"""

from __future__ import annotations

import time

import pytest

from claude_code.ui.message_list import (
    MessageRenderer,
    MessageRenderResult,
    MessageRow,
    MessageRowState,
    RenderedMessage,
    VirtualMessageList,
    VirtualMessageListState,
)


class TestVirtualMessageListState:
    """Tests for VirtualMessageListState."""

    def test_create(self) -> None:
        """Test creating state."""
        state = VirtualMessageListState()
        assert state.message_count == 0
        assert state.scroll_position == 0
        assert state.sticky_prompt_index == -1
        assert state.visible_start == 0
        assert state.visible_end == 0
        assert state.total_height == 0

    def test_with_messages(self) -> None:
        """Test state with messages."""
        state = VirtualMessageListState(message_count=50)
        assert state.message_count == 50

    def test_update_scroll(self) -> None:
        """Test updating scroll position."""
        state = VirtualMessageListState(message_count=100)
        state.update_scroll(scroll_position=200, viewport_height=50)
        assert state.scroll_position == 200
        assert state.viewport_height == 50

    def test_set_sticky_prompt(self) -> None:
        """Test setting sticky prompt index."""
        state = VirtualMessageListState(message_count=50)
        state.set_sticky_prompt(42)
        assert state.sticky_prompt_index == 42

    def test_set_sticky_prompt_negative_clears(self) -> None:
        """Test setting negative sticky prompt clears it."""
        state = VirtualMessageListState(message_count=50, sticky_prompt_index=10)
        state.set_sticky_prompt(-1)
        assert state.sticky_prompt_index == -1


class TestMessageRowState:
    """Tests for MessageRowState."""

    def test_create(self) -> None:
        """Test creating row state."""
        state = MessageRowState(message_id="msg-1")
        assert state.message_id == "msg-1"
        assert state.is_selected is False
        assert state.is_expanded is False
        assert state.height is None
        assert state.offset is None

    def test_with_select(self) -> None:
        """Test state with selection."""
        state = MessageRowState(message_id="msg-1", is_selected=True)
        assert state.is_selected is True

    def test_with_expand(self) -> None:
        """Test state with expand."""
        state = MessageRowState(message_id="msg-1", is_expanded=True)
        assert state.is_expanded is True

    def test_update_height(self) -> None:
        """Test updating measured height."""
        state = MessageRowState(message_id="msg-1")
        state.update_height(25)
        assert state.height == 25

    def test_update_offset(self) -> None:
        """Test updating offset."""
        state = MessageRowState(message_id="msg-1")
        state.update_offset(100)
        assert state.offset == 100

    def test_toggle_expand(self) -> None:
        """Test toggling expand."""
        state = MessageRowState(message_id="msg-1")
        assert state.is_expanded is False
        state.toggle_expand()
        assert state.is_expanded is True
        state.toggle_expand()
        assert state.is_expanded is False


class TestRenderedMessage:
    """Tests for RenderedMessage."""

    def test_create(self) -> None:
        """Test creating rendered message."""
        rendered = RenderedMessage(message_id="msg-1", lines=5)
        assert rendered.message_id == "msg-1"
        assert rendered.lines == 5
        assert rendered.is_truncated is False
        assert rendered.truncated_at is None

    def test_with_truncation(self) -> None:
        """Test rendered with truncation."""
        rendered = RenderedMessage(
            message_id="msg-1",
            lines=100,
            is_truncated=True,
            truncated_at=50,
        )
        assert rendered.is_truncated is True
        assert rendered.truncated_at == 50


class TestMessageRenderResult:
    """Tests for MessageRenderResult."""

    def test_create(self) -> None:
        """Test creating render result."""
        result = MessageRenderResult(message_id="msg-1", rendered_lines=5)
        assert result.message_id == "msg-1"
        assert result.rendered_lines == 5
        assert result.has_error is False
        assert result.error_message is None

    def test_with_error(self) -> None:
        """Test render result with error."""
        result = MessageRenderResult(
            message_id="msg-1",
            rendered_lines=0,
            has_error=True,
            error_message="Failed to render",
        )
        assert result.has_error is True
        assert result.error_message == "Failed to render"


class TestMessageRenderer:
    """Tests for MessageRenderer."""

    def test_create(self) -> None:
        """Test creating renderer."""
        renderer = MessageRenderer()
        assert renderer.max_width == 80
        assert renderer.truncate_threshold == 1000

    def test_render_plain_text(self) -> None:
        """Test rendering plain text."""
        renderer = MessageRenderer()
        result = renderer.render_text("Hello world", message_id="msg-1")
        assert result.message_id == "msg-1"
        assert result.rendered_lines >= 1
        assert result.has_error is False

    def test_render_empty_text(self) -> None:
        """Test rendering empty text."""
        renderer = MessageRenderer()
        result = renderer.render_text("", message_id="msg-1")
        assert result.message_id == "msg-1"
        assert result.rendered_lines >= 1  # Empty text still renders

    def test_render_with_max_width(self) -> None:
        """Test rendering with custom max width."""
        renderer = MessageRenderer(max_width=40)
        text = "This is a very long line that should wrap at max width"
        result = renderer.render_text(text, message_id="msg-1")
        assert result.has_error is False
        # The line should have wrapped (57 chars at width 40 = 2 lines)
        assert result.rendered_lines >= 2

    def test_render_multiline(self) -> None:
        """Test rendering multiline text."""
        renderer = MessageRenderer()
        text = "Line 1\nLine 2\nLine 3"
        result = renderer.render_text(text, message_id="msg-1")
        assert result.message_id == "msg-1"
        assert result.has_error is False

    def test_render_truncation(self) -> None:
        """Test truncation for very long content."""
        renderer = MessageRenderer(truncate_threshold=100)
        long_text = "x" * 200
        result = renderer.render_text(long_text, message_id="msg-1")
        assert result.has_error is False
        assert result.rendered_lines >= 1


class TestVirtualMessageList:
    """Tests for VirtualMessageList."""

    def test_create(self) -> None:
        """Test creating virtual message list."""
        vml = VirtualMessageList()
        assert vml.message_count == 0
        assert vml.get_state() is not None
        assert vml.get_state().message_count == 0

    def test_add_message(self) -> None:
        """Test adding a message."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        assert vml.message_count == 1
        assert vml.get_message_lines("msg-1") == 5

    def test_add_multiple_messages(self) -> None:
        """Test adding multiple messages."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        vml.add_message(message_id="msg-2", lines=3)
        vml.add_message(message_id="msg-3", lines=7)
        assert vml.message_count == 3

    def test_remove_message(self) -> None:
        """Test removing a message."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        assert vml.message_count == 1
        vml.remove_message("msg-1")
        assert vml.message_count == 0

    def test_remove_nonexistent(self) -> None:
        """Test removing nonexistent message does not error."""
        vml = VirtualMessageList()
        vml.remove_message("nonexistent")  # Should not raise
        assert vml.message_count == 0

    def test_update_message_height(self) -> None:
        """Test updating measured height."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        vml.update_message_height("msg-1", 25)
        assert vml.get_message_lines("msg-1") == 25

    def test_get_message_lines_missing(self) -> None:
        """Test getting lines for missing message."""
        vml = VirtualMessageList()
        assert vml.get_message_lines("nonexistent") == 3  # default estimate

    def test_scroll_to_index(self) -> None:
        """Test scrolling to message index."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        vml.add_message(message_id="msg-2", lines=3)
        vml.add_message(message_id="msg-3", lines=7)
        pos = vml.scroll_to_index(2)
        assert pos >= 0  # Should return a valid scroll position

    def test_scroll_to_index_out_of_range(self) -> None:
        """Test scrolling to out-of-range index."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        pos = vml.scroll_to_index(100)
        assert pos == 0

    def test_compute_visible_range(self) -> None:
        """Test computing visible range."""
        vml = VirtualMessageList()
        for i in range(50):
            vml.add_message(message_id=f"msg-{i}", lines=5)
        start, end = vml.compute_visible_range(viewport_top=0, viewport_height=50)
        assert start >= 0
        assert end > start
        assert end <= vml.message_count

    def test_set_sticky_prompt(self) -> None:
        """Test setting sticky prompt."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        vml.add_message(message_id="msg-2", lines=3)
        vml.set_sticky_prompt(1)
        assert vml.get_state().sticky_prompt_index == 1

    def test_clear_sticky_prompt(self) -> None:
        """Test clearing sticky prompt."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        vml.set_sticky_prompt(0)
        vml.set_sticky_prompt(-1)
        assert vml.get_state().sticky_prompt_index == -1

    def test_total_height(self) -> None:
        """Test total content height."""
        vml = VirtualMessageList()
        vml.add_message(message_id="msg-1", lines=5)
        vml.add_message(message_id="msg-2", lines=3)
        vml.add_message(message_id="msg-3", lines=7)
        total = vml.get_total_height()
        # Total height is sum of all measured heights
        assert total >= 9  # 3 items * default estimate 3

    def test_visible_range_with_offset(self) -> None:
        """Test visible range computation with scroll offset."""
        vml = VirtualMessageList()
        for i in range(100):
            vml.add_message(message_id=f"msg-{i}", lines=5)
        # At scroll position 100
        start, end = vml.compute_visible_range(viewport_top=100, viewport_height=50)
        assert start >= 0
        assert end > start
