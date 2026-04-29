"""Tests for UI layout components (FullscreenLayout, ScrollContainer)."""

from __future__ import annotations

import pytest

from claude_code.ui.layout import (
    FullscreenLayout,
    LayoutRegion,
    LayoutSlot,
    ScrollContainer,
)


class TestLayoutSlot:
    """Tests for LayoutSlot enum."""

    def test_all_slots_exist(self) -> None:
        """All expected slots exist."""
        assert LayoutSlot.SCROLLBOX == "scrollbox"
        assert LayoutSlot.BOTTOM == "bottom"
        assert LayoutSlot.MODAL == "modal"
        assert LayoutSlot.BOTTOM_FLOAT == "bottom_float"


class TestLayoutRegion:
    """Tests for LayoutRegion."""

    def test_default_values(self) -> None:
        """LayoutRegion has correct defaults."""
        region = LayoutRegion()
        assert region.slot == LayoutSlot.SCROLLBOX
        assert region.visible is True
        assert region.content is None


class TestScrollContainer:
    """Tests for ScrollContainer."""

    def test_default_values(self) -> None:
        """ScrollContainer has correct defaults."""
        sc = ScrollContainer()
        assert sc.scroll_position == 0
        assert sc.viewport_height == 0
        assert sc.max_scroll == 0
        assert sc.show_logo is False

    def test_scroll_by(self) -> None:
        """scroll_by works correctly."""
        sc = ScrollContainer(max_scroll=100)
        sc.scroll_by(10)
        assert sc.scroll_position == 10
        sc.scroll_by(-5)
        assert sc.scroll_position == 5

    def test_scroll_by_bounds(self) -> None:
        """scroll_by respects bounds."""
        sc = ScrollContainer(max_scroll=100)
        sc.scroll_by(200)
        assert sc.scroll_position == 100
        sc.scroll_position = 50
        sc.scroll_by(-200)
        assert sc.scroll_position == 0

    def test_scroll_to(self) -> None:
        """scroll_to works correctly."""
        sc = ScrollContainer(max_scroll=100)
        sc.scroll_to(50)
        assert sc.scroll_position == 50

    def test_scroll_to_bounds(self) -> None:
        """scroll_to respects bounds."""
        sc = ScrollContainer(max_scroll=100)
        sc.scroll_to(200)
        assert sc.scroll_position == 100
        sc.scroll_to(-10)
        assert sc.scroll_position == 0


class TestFullscreenLayout:
    """Tests for FullscreenLayout."""

    def test_default_values(self) -> None:
        """FullscreenLayout has correct defaults."""
        layout = FullscreenLayout()
        assert layout.modal_visible is False
        assert layout.bottom_float_visible is False
        assert layout.is_loading is False
        assert layout.show_status_notices is True

    def test_is_slot_visible(self) -> None:
        """is_slot_visible works correctly."""
        layout = FullscreenLayout()

        # SCROLLBOX and BOTTOM are always visible
        assert layout.is_slot_visible(LayoutSlot.SCROLLBOX) is True
        assert layout.is_slot_visible(LayoutSlot.BOTTOM) is True

        # MODAL and BOTTOM_FLOAT depend on state
        assert layout.is_slot_visible(LayoutSlot.MODAL) is False
        assert layout.is_slot_visible(LayoutSlot.BOTTOM_FLOAT) is False

        layout.modal_visible = True
        assert layout.is_slot_visible(LayoutSlot.MODAL) is True

        layout.bottom_float_visible = True
        assert layout.is_slot_visible(LayoutSlot.BOTTOM_FLOAT) is True

    def test_update_scroll(self) -> None:
        """update_scroll updates container state."""
        layout = FullscreenLayout()
        layout.update_scroll(
            scroll_position=50,
            viewport_height=24,
            max_scroll=200,
        )
        assert layout.scroll_container.scroll_position == 50
        assert layout.scroll_container.viewport_height == 24
        assert layout.scroll_container.max_scroll == 200

    def test_set_loading(self) -> None:
        """set_loading works correctly."""
        layout = FullscreenLayout()
        assert layout.is_loading is False
        layout.set_loading(True)
        assert layout.is_loading is True
        layout.set_loading(False)
        assert layout.is_loading is False

    def test_show_hide_modal(self) -> None:
        """show_modal and hide_modal work."""
        layout = FullscreenLayout()
        assert layout.modal_visible is False
        layout.show_modal()
        assert layout.modal_visible is True
        layout.hide_modal()
        assert layout.modal_visible is False

    def test_toggle_bottom_float(self) -> None:
        """toggle_bottom_float works."""
        layout = FullscreenLayout()
        assert layout.bottom_float_visible is False
        layout.toggle_bottom_float()
        assert layout.bottom_float_visible is True
        layout.toggle_bottom_float()
        assert layout.bottom_float_visible is False
