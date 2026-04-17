"""UI component library for Claude Code TUI.

TypeScript equivalent: src/components/design-system/*, src/state/store.ts

This module provides reusable UI components and state management:
- Theme system with color definitions
- State Store with subscription support
- Base widget components (Dialog, Pane, Box, etc.)
- Virtual scrolling for message lists
- Input state types and helpers

The component system is designed for use with Textual.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Generic, TypeVar

# =============================================================================
# Theme System
# =============================================================================


class Colors(StrEnum):
    """Color constants matching Claude Code design system."""

    PERMISSION = "#f0b000"  # Yellow for permission dialogs
    ERROR = "#f85149"  # Red for errors
    SUCCESS = "#3fb950"  # Green for success
    PRIMARY = "#58a6ff"  # Blue for primary actions
    INFO = "#8b949e"  # Gray for info
    DIM = "#6e7681"  # Dim text
    WARNING = "#d29922"  # Warning yellow
    TEXT = "#e6edf3"  # Primary text
    TEXT_MUTED = "#8b949e"  # Muted text


@dataclass
class Theme:
    """Theme configuration for the TUI.

    Attributes:
        primary: Primary accent color.
        secondary: Secondary color.
        dim: Dimmed/muted color.
        error: Error color.
        warning: Warning color.
        success: Success color.
        permission: Permission dialog color.
        info: Info text color.
        text: Primary text color.
        text_muted: Muted text color.
        surface: Background surface color.
        surface_darken: Darkened surface color.
    """

    primary: str = Colors.PRIMARY.value
    secondary: str = Colors.INFO.value
    dim: str = Colors.DIM.value
    error: str = Colors.ERROR.value
    warning: str = Colors.WARNING.value
    success: str = Colors.SUCCESS.value
    permission: str = Colors.PERMISSION.value
    info: str = Colors.INFO.value
    text: str = Colors.TEXT.value
    text_muted: str = Colors.TEXT_MUTED.value
    surface: str = "#0d1117"
    surface_darken: str = "#161b22"

    def to_dict(self) -> dict[str, str]:
        """Convert theme to dictionary for Textual."""
        return {
            "primary": self.primary,
            "secondary": self.secondary,
            "dim": self.dim,
            "error": self.error,
            "warning": self.warning,
            "success": self.success,
            "permission": self.permission,
            "info": self.info,
            "text": self.text,
            "text-muted": self.text_muted,
            "surface": self.surface,
            "surface-darken": self.surface_darken,
        }


# Global default theme
DEFAULT_THEME = Theme()


# =============================================================================
# State Store
# =============================================================================

T = TypeVar("T")


@dataclass
class Store(Generic[T]):
    """Reactive state store with subscription support.

    TypeScript equivalent: src/state/store.ts Store

    Attributes:
        _state: Current state value.
        _listeners: Set of listener callbacks.
        _on_change: Optional change callback.

    Example:
        store = Store({"count": 0})
        store.subscribe(lambda: print("changed"))
        store.set_state(lambda s: {"count": s["count"] + 1})
    """

    _state: T = field(default=None)  # type: ignore[assignment]
    _listeners: set[Callable[[], None]] = field(default_factory=set)
    _on_change: Callable[[T, T], None] | None = None

    def __init__(
        self,
        initial_state: T,
        on_change: Callable[[T, T], None] | None = None,
    ) -> None:
        """Initialize the store.

        Args:
            initial_state: Initial state value.
            on_change: Optional callback fired on state changes.
        """
        self._state = initial_state
        self._listeners: set[Callable[[], None]] = set()
        self._on_change = on_change

    def get_state(self) -> T:
        """Get current state.

        Returns:
            The current state value.
        """
        return self._state

    def set_state(self, updater: Callable[[T], T]) -> None:
        """Update state with a pure function.

        Args:
            updater: Function that takes current state and returns new state.
        """
        prev = self._state
        next_state = updater(prev)
        # Use equality check for dicts
        if isinstance(next_state, dict) and isinstance(prev, dict):
            if next_state == prev:
                return
        elif next_state == prev:
            return

        self._state = next_state

        # Fire on_change callback
        if self._on_change:
            self._on_change(next_state, prev)

        # Notify listeners
        for listener in self._listeners:
            listener()

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to state changes.

        Args:
            listener: Callback to invoke on state changes.

        Returns:
            Unsubscribe function.
        """
        self._listeners.add(listener)

        def unsubscribe() -> None:
            self._listeners.discard(listener)

        return unsubscribe

    def __len__(self) -> int:
        """Return number of listeners."""
        return len(self._listeners)


# =============================================================================
# Input State Types
# =============================================================================


class PromptInputMode(StrEnum):
    """Prompt input modes."""

    EDIT = "edit"
    VIM_NORMAL = "vim_normal"
    VIM_INSERT = "vim_insert"
    VIM_VISUAL = "vim_visual"


# =============================================================================
# Virtual Scroll Implementation
# =============================================================================


@dataclass
class VirtualScrollResult(Generic[T]):
    """Result of virtual scroll computation.

    Handles virtualized rendering of scrollable content with:
    - Height caching for items not yet measured
    - Overscan to prevent blank areas during scroll
    - Item range computation for viewport

    Attributes:
        DEFAULT_ESTIMATE: Default rows for unmeasured items.
        OVERSCAN_ROWS: Rows of overscan above/below viewport.
        MAX_MOUNTED_ITEMS: Cap on fiber/allocation.
        SLIDE_STEP: Max new items per commit.
    """

    DEFAULT_ESTIMATE: int = 3
    OVERSCAN_ROWS: int = 80
    MAX_MOUNTED_ITEMS: int = 300
    SLIDE_STEP: int = 25

    _height_cache: dict[int, int] = field(default_factory=dict)
    _offsets: list[int] = field(default_factory=list)
    _items: list[T] = field(default_factory=list)

    def set_items(self, items: list[T]) -> None:
        """Set items and initialize offsets.

        Args:
            items: List of items to virtualize.
        """
        self._items = list(items)
        self._recompute_offsets(0)

    def compute_range(
        self,
        viewport_top: int,
        viewport_height: int,
    ) -> tuple[int, int]:
        """Compute visible range with overscan.

        Args:
            viewport_top: Top position of viewport.
            viewport_height: Height of viewport.

        Returns:
            Tuple of (start_index, end_index) for visible items.
        """
        if not self._offsets:
            return 0, 0

        # Find start index using binary search
        start_idx = max(0, bisect.bisect_right(self._offsets, viewport_top) - 1)

        viewport_bottom = viewport_top + viewport_height
        end_idx = bisect.bisect_left(self._offsets, viewport_bottom)

        # Apply overscan
        start_idx = max(0, start_idx - self.OVERSCAN_ROWS)
        end_idx = min(len(self._items), end_idx + self.OVERSCAN_ROWS)

        # Cap at max mounted items
        if end_idx - start_idx > self.MAX_MOUNTED_ITEMS:
            end_idx = start_idx + self.MAX_MOUNTED_ITEMS

        return start_idx, end_idx

    def measure_item(self, index: int, height: int) -> None:
        """Cache measured height after layout.

        Args:
            index: Item index.
            height: Measured height in rows.
        """
        if self._height_cache.get(index) == height:
            return
        self._height_cache[index] = height
        self._recompute_offsets(index)

    def _recompute_offsets(self, from_index: int) -> None:
        """Recompute offsets array from from_index onward.

        Args:
            from_index: Start recomputing from this index.
        """
        # Extend offsets list if needed
        while len(self._offsets) < len(self._items):
            self._offsets.append(0)

        for i in range(from_index, len(self._items)):
            if i == 0:
                # First item starts at offset 0
                self._offsets[i] = 0
            else:
                prev_end = self._offsets[i - 1] + self._height_cache.get(i - 1, self.DEFAULT_ESTIMATE)
                self._offsets[i] = prev_end

    def get_item_height(self, index: int) -> int:
        """Get height of item at index.

        Args:
            index: Item index.

        Returns:
            Height of the item.
        """
        return self._height_cache.get(index, self.DEFAULT_ESTIMATE)

    def get_total_height(self) -> int:
        """Get total height of all items.

        Returns:
            Total height in rows.
        """
        if not self._offsets or not self._items:
            return 0
        # Last offset + height of last item
        last_offset = self._offsets[-1]
        last_height = self._height_cache.get(len(self._items) - 1, self.DEFAULT_ESTIMATE)
        return last_offset + last_height

    def scroll_to_index(self, index: int) -> int:
        """Get scroll position for item at index.

        Args:
            index: Item index to scroll to.

        Returns:
            Scroll position (offset).
        """
        if index < len(self._offsets):
            return self._offsets[index]
        return 0

    @property
    def item_count(self) -> int:
        """Return number of items."""
        return len(self._items)


# =============================================================================
# Message Types
# =============================================================================


class MessageType(StrEnum):
    """Message types in the UI."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"


@dataclass
class MessageDisplay:
    """Display representation of a message.

    Attributes:
        id: Unique message identifier.
        type: Message type.
        content: Text content or structured content.
        timestamp: Unix timestamp.
        is_meta: Whether this is a metadata message.
        is_hidden: Whether message is hidden (verbose mode).
    """

    id: str
    type: MessageType
    content: str | list[dict[str, Any]]
    timestamp: float
    is_meta: bool = False
    is_hidden: bool = False

    @classmethod
    def from_text(cls, text: str, msg_type: MessageType = MessageType.ASSISTANT) -> MessageDisplay:
        """Create a simple text message.

        Args:
            text: Text content.
            msg_type: Message type.

        Returns:
            New MessageDisplay instance.
        """
        import time

        return cls(
            id="",
            type=msg_type,
            content=text,
            timestamp=time.time(),
        )


# =============================================================================
# Dialog Components
# =============================================================================


@dataclass
class DialogStyle:
    """Styling options for Dialog component."""

    color: str = Colors.PERMISSION.value
    hide_border: bool = False
    hide_input_guide: bool = False


# =============================================================================
# Keyboard Shortcut
# =============================================================================


@dataclass
class KeyboardShortcut:
    """Represents a keyboard shortcut.

    Attributes:
        key: The key name.
        action: The action to trigger.
        context: Optional context for the binding.
        description: Human-readable description.
    """

    key: str
    action: str
    context: str | None = None
    description: str | None = None


# =============================================================================
# Scroll State
# =============================================================================


@dataclass
class ScrollState:
    """State for scroll position tracking.

    Attributes:
        position: Current scroll position.
        viewport_height: Current viewport height.
        max_position: Maximum scroll position.
        sticky_prompt_index: Index of sticky prompt (-1 if none).
    """

    position: int = 0
    viewport_height: int = 0
    max_position: int = 0
    sticky_prompt_index: int = -1

    def update_viewport(self, height: int, max_pos: int) -> None:
        """Update viewport dimensions.

        Args:
            height: New viewport height.
            max_pos: New max position.
        """
        self.viewport_height = height
        self.max_position = max_pos

    def scroll_by(self, delta: int) -> None:
        """Scroll by delta amount.

        Args:
            delta: Amount to scroll.
        """
        self.position = max(0, min(self.max_position, self.position + delta))

    def scroll_to(self, position: int) -> None:
        """Scroll to absolute position.

        Args:
            position: Target position.
        """
        self.position = max(0, min(self.max_position, position))
