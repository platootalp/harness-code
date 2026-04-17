"""
Tests for UI layout components - FullscreenLayout.
"""

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

    def test_slot_values(self) -> None:
        """Test LayoutSlot enum values."""
        assert LayoutSlot.SCROLLBOX.value == "scrollbox"
        assert LayoutSlot.BOTTOM.value == "bottom"
        assert LayoutSlot.MODAL.value == "modal"
        assert LayoutSlot.BOTTOM_FLOAT.value == "bottom_float"

    def test_slot_is_string(self) -> None:
        """Test LayoutSlot is a string enum."""
        assert isinstance(LayoutSlot.SCROLLBOX, str)


class TestLayoutRegion:
    """Tests for LayoutRegion dataclass."""

    def test_create(self) -> None:
        """Test creating a layout region."""
        region = LayoutRegion(slot=LayoutSlot.SCROLLBOX, visible=True)
        assert region.slot == LayoutSlot.SCROLLBOX
        assert region.visible is True
        assert region.content is None

    def test_with_content(self) -> None:
        """Test creating region with content."""
        region = LayoutRegion(
            slot=LayoutSlot.BOTTOM,
            visible=True,
            content="prompt input content",
        )
        assert region.content == "prompt input content"

    def test_defaults(self) -> None:
        """Test default values."""
        region = LayoutRegion(slot=LayoutSlot.MODAL)
        assert region.visible is True
        assert region.content is None


class TestScrollContainer:
    """Tests for ScrollContainer dataclass."""

    def test_create(self) -> None:
        """Test creating scroll container."""
        container = ScrollContainer()
        assert container.scroll_position == 0
        assert container.viewport_height == 0
        assert container.max_scroll == 0
        assert container.show_logo is False

    def test_with_custom_values(self) -> None:
        """Test with custom scroll values."""
        container = ScrollContainer(
            scroll_position=100,
            viewport_height=50,
            max_scroll=500,
            show_logo=True,
        )
        assert container.scroll_position == 100
        assert container.viewport_height == 50
        assert container.max_scroll == 500
        assert container.show_logo is True

    def test_scroll_by(self) -> None:
        """Test scrolling by delta."""
        container = ScrollContainer(max_scroll=500)
        container.scroll_by(50)
        assert container.scroll_position == 50

    def test_scroll_by_clamp(self) -> None:
        """Test scroll clamping at boundaries."""
        container = ScrollContainer(max_scroll=100)
        container.scroll_by(-50)
        assert container.scroll_position == 0
        container.scroll_position = 100
        container.scroll_by(50)
        assert container.scroll_position == 100

    def test_scroll_to(self) -> None:
        """Test scrolling to position."""
        container = ScrollContainer(max_scroll=500)
        container.scroll_to(200)
        assert container.scroll_position == 200

    def test_scroll_to_clamp(self) -> None:
        """Test scroll_to clamping."""
        container = ScrollContainer(max_scroll=100)
        container.scroll_to(-10)
        assert container.scroll_position == 0
        container.scroll_to(200)
        assert container.scroll_position == 100


class TestFullscreenLayout:
    """Tests for FullscreenLayout dataclass."""

    def test_create(self) -> None:
        """Test creating fullscreen layout."""
        layout = FullscreenLayout()
        assert layout.scroll_container is not None
        assert layout.scroll_container.scroll_position == 0
        assert layout.modal_visible is False
        assert layout.bottom_float_visible is False
        assert layout.is_loading is False
        assert layout.show_status_notices is True

    def test_with_modal(self) -> None:
        """Test layout with modal visible."""
        layout = FullscreenLayout(modal_visible=True)
        assert layout.modal_visible is True

    def test_with_bottom_float(self) -> None:
        """Test layout with bottom float visible."""
        layout = FullscreenLayout(bottom_float_visible=True)
        assert layout.bottom_float_visible is True

    def test_slot_visibility(self) -> None:
        """Test slot visibility defaults."""
        layout = FullscreenLayout()
        assert layout.is_slot_visible(LayoutSlot.SCROLLBOX) is True
        assert layout.is_slot_visible(LayoutSlot.BOTTOM) is True
        assert layout.is_slot_visible(LayoutSlot.MODAL) is False
        assert layout.is_slot_visible(LayoutSlot.BOTTOM_FLOAT) is False

    def test_slot_visibility_with_modal(self) -> None:
        """Test slot visibility when modal is open."""
        layout = FullscreenLayout(modal_visible=True)
        # Modal overlays scrollbox but bottom stays accessible
        assert layout.is_slot_visible(LayoutSlot.SCROLLBOX) is True
        assert layout.is_slot_visible(LayoutSlot.BOTTOM) is True
        assert layout.is_slot_visible(LayoutSlot.MODAL) is True

    def test_update_scroll(self) -> None:
        """Test updating scroll position."""
        layout = FullscreenLayout()
        layout.update_scroll(scroll_position=150, viewport_height=50, max_scroll=500)
        assert layout.scroll_container.scroll_position == 150
        assert layout.scroll_container.viewport_height == 50
        assert layout.scroll_container.max_scroll == 500

    def test_toggle_loading(self) -> None:
        """Test toggling loading state."""
        layout = FullscreenLayout()
        assert layout.is_loading is False
        layout.set_loading(True)
        assert layout.is_loading is True
        layout.set_loading(False)
        assert layout.is_loading is False
