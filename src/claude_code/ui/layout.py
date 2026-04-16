"""UI layout components for Claude Code TUI.

TypeScript equivalent: FullscreenLayout, ScrollBox components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Layout Regions
# =============================================================================


class LayoutSlot(StrEnum):
    """Layout slot identifiers for the fullscreen layout.

    The main application is divided into these regions:
    - SCROLLBOX: Main scrollable content area for messages
    - BOTTOM: Pinned bottom area for prompt input
    - MODAL: Overlay modal dialogs
    - BOTTOM_FLOAT: Floating content over scrollback
    """

    SCROLLBOX = "scrollbox"
    BOTTOM = "bottom"
    MODAL = "modal"
    BOTTOM_FLOAT = "bottom_float"


@dataclass
class LayoutRegion:
    """A region in the layout.

    Attributes:
        slot: Which layout slot this region occupies.
        visible: Whether the region is visible.
        content: Optional content for the region.
    """

    slot: LayoutSlot = LayoutSlot.SCROLLBOX
    visible: bool = True
    content: Any = None


# =============================================================================
# Scroll Container
# =============================================================================


@dataclass
class ScrollContainer:
    """State for the scroll container.

    Attributes:
        scroll_position: Current scroll position.
        viewport_height: Height of the visible viewport.
        max_scroll: Maximum scroll position.
        show_logo: Whether to show the logo at top.
    """

    scroll_position: int = 0
    viewport_height: int = 0
    max_scroll: int = 0
    show_logo: bool = False

    def scroll_by(self, delta: int) -> None:
        """Scroll by delta amount.

        Args:
            delta: Amount to scroll (positive = down, negative = up).
        """
        new_pos = self.scroll_position + delta
        self.scroll_position = max(0, min(self.max_scroll, new_pos))

    def scroll_to(self, position: int) -> None:
        """Scroll to absolute position.

        Args:
            position: Target scroll position.
        """
        self.scroll_position = max(0, min(self.max_scroll, position))


# =============================================================================
# Fullscreen Layout
# =============================================================================


@dataclass
class FullscreenLayout:
    """Fullscreen layout container for Claude Code TUI.

    TypeScript equivalent: FullscreenLayout component.

    The layout consists of:
    - scroll_container: Main scrollable message area
    - modal_visible: Whether a modal overlay is shown
    - bottom_float_visible: Whether floating bottom content is shown
    - is_loading: Whether loading indicator should be shown
    - show_status_notices: Whether status notices are visible
    """

    scroll_container: ScrollContainer = field(default_factory=ScrollContainer)
    modal_visible: bool = False
    bottom_float_visible: bool = False
    is_loading: bool = False
    show_status_notices: bool = True

    def is_slot_visible(self, slot: LayoutSlot) -> bool:
        """Check if a layout slot is currently visible.

        Args:
            slot: The layout slot to check.

        Returns:
            True if the slot is visible.
        """
        if slot == LayoutSlot.MODAL:
            return self.modal_visible
        if slot == LayoutSlot.BOTTOM_FLOAT:
            return self.bottom_float_visible
        # SCROLLBOX and BOTTOM are always visible unless loading
        return True

    def update_scroll(
        self,
        scroll_position: int,
        viewport_height: int,
        max_scroll: int,
    ) -> None:
        """Update scroll container dimensions and position.

        Args:
            scroll_position: Current scroll position.
            viewport_height: Height of the viewport.
            max_scroll: Maximum scroll position.
        """
        self.scroll_container.scroll_position = scroll_position
        self.scroll_container.viewport_height = viewport_height
        self.scroll_container.max_scroll = max_scroll

    def set_loading(self, loading: bool) -> None:
        """Set loading state.

        Args:
            loading: Whether to show loading indicator.
        """
        self.is_loading = loading

    def show_modal(self) -> None:
        """Show the modal overlay."""
        self.modal_visible = True

    def hide_modal(self) -> None:
        """Hide the modal overlay."""
        self.modal_visible = False

    def toggle_bottom_float(self) -> None:
        """Toggle bottom float visibility."""
        self.bottom_float_visible = not self.bottom_float_visible
