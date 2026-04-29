"""UI message list components for Claude Code TUI.

TypeScript equivalent: VirtualMessageList, MessageRow, message rendering chain.

Provides virtualized message list rendering and message rendering utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from claude_code.ui.components import VirtualScrollResult

if TYPE_CHECKING:
    pass


# =============================================================================
# Message List State
# =============================================================================


@dataclass
class VirtualMessageListState:
    """State for the virtual message list.

    Attributes:
        message_count: Number of messages in the list.
        scroll_position: Current scroll position.
        viewport_height: Height of the viewport.
        sticky_prompt_index: Index of sticky prompt (-1 if none).
        visible_start: Start index of visible range.
        visible_end: End index of visible range.
        total_height: Total rendered height.
    """

    message_count: int = 0
    scroll_position: int = 0
    viewport_height: int = 0
    sticky_prompt_index: int = -1
    visible_start: int = 0
    visible_end: int = 0
    total_height: int = 0

    def update_scroll(self, scroll_position: int, viewport_height: int) -> None:
        """Update scroll position.

        Args:
            scroll_position: Current scroll position.
            viewport_height: Height of the viewport.
        """
        self.scroll_position = scroll_position
        self.viewport_height = viewport_height

    def set_sticky_prompt(self, index: int) -> None:
        """Set sticky prompt index.

        Args:
            index: Index of the sticky prompt, or -1 to clear.
        """
        self.sticky_prompt_index = index


@dataclass
class MessageRowState:
    """State for an individual message row.

    Attributes:
        message_id: Unique identifier for the message.
        is_selected: Whether the row is selected.
        is_expanded: Whether the row is expanded.
        height: Measured render height.
        offset: Render offset from top.
    """

    message_id: str
    is_selected: bool = False
    is_expanded: bool = False
    height: int | None = None
    offset: int | None = None

    def update_height(self, height: int) -> None:
        """Update measured height.

        Args:
            height: New measured height.
        """
        self.height = height

    def update_offset(self, offset: int) -> None:
        """Update render offset.

        Args:
            offset: New offset from top.
        """
        self.offset = offset

    def toggle_expand(self) -> None:
        """Toggle expanded state."""
        self.is_expanded = not self.is_expanded


# =============================================================================
# Message Rendering
# =============================================================================


@dataclass
class RenderedMessage:
    """A rendered message.

    Attributes:
        message_id: Unique identifier.
        lines: Number of rendered lines.
        is_truncated: Whether content was truncated.
        truncated_at: Line at which truncation occurred.
    """

    message_id: str
    lines: int
    is_truncated: bool = False
    truncated_at: int | None = None


@dataclass
class MessageRenderResult:
    """Result of rendering a message.

    Attributes:
        message_id: Unique identifier.
        rendered_lines: Number of lines rendered.
        has_error: Whether rendering produced an error.
        error_message: Error message if any.
    """

    message_id: str
    rendered_lines: int
    has_error: bool = False
    error_message: str | None = None


class MessageRenderer:
    """Renders message content.

    TypeScript equivalent: message rendering chain in messages/*.tsx.

    Attributes:
        max_width: Maximum line width for wrapping.
        truncate_threshold: Line count at which to truncate.
    """

    def __init__(
        self,
        max_width: int = 80,
        truncate_threshold: int = 1000,
    ) -> None:
        """Initialize message renderer.

        Args:
            max_width: Maximum line width.
            truncate_threshold: Line count at which to truncate.
        """
        self.max_width = max_width
        self.truncate_threshold = truncate_threshold

    def render_text(
        self,
        text: str,
        message_id: str,
    ) -> MessageRenderResult:
        """Render plain text content.

        Args:
            text: Text content to render.
            message_id: Unique identifier for the message.

        Returns:
            Render result with line count.
        """
        try:
            lines = self._count_rendered_lines(text)
            return MessageRenderResult(
                message_id=message_id,
                rendered_lines=lines,
            )
        except Exception as e:
            return MessageRenderResult(
                message_id=message_id,
                rendered_lines=0,
                has_error=True,
                error_message=str(e),
            )

    def _count_rendered_lines(self, text: str) -> int:
        """Count rendered lines for text.

        Args:
            text: Text content.

        Returns:
            Number of rendered lines.
        """
        if not text:
            return 1

        count = 0
        for line in text.split("\n"):
            if len(line) <= self.max_width:
                count += 1
            else:
                count += (len(line) + self.max_width - 1) // self.max_width
        return max(1, count)


@dataclass
class MessageRow:
    """A message row in the list.

    TypeScript equivalent: MessageRow.tsx

    Attributes:
        message_id: Unique identifier.
        content: Message content.
        row_state: Row rendering state.
    """

    message_id: str
    content: str | list[dict[str, Any]] = ""
    row_state: MessageRowState | None = None

    def __post_init__(self) -> None:
        """Initialize row state if not provided."""
        if self.row_state is None or self.row_state.message_id != self.message_id:
            self.row_state = MessageRowState(message_id=self.message_id)


# =============================================================================
# Virtual Message List
# =============================================================================


class VirtualMessageList:
    """Virtualized message list.

    TypeScript equivalent: VirtualMessageList.tsx

    Uses virtual scrolling to efficiently render large message lists.
    Combines VirtualScrollResult with message-specific state.
    """

    def __init__(self) -> None:
        """Initialize virtual message list."""
        self._state = VirtualMessageListState()
        self._scroll = VirtualScrollResult[str]()
        self._row_heights: dict[str, int] = {}

    @property
    def message_count(self) -> int:
        """Return number of messages."""
        return self._state.message_count

    def get_state(self) -> VirtualMessageListState:
        """Get current state.

        Returns:
            Current list state.
        """
        return self._state

    def add_message(self, message_id: str, lines: int) -> None:
        """Add a message to the list.

        Args:
            message_id: Unique identifier.
            lines: Estimated line count.
        """
        if message_id in self._row_heights:
            return
        self._row_heights[message_id] = lines
        self._state.message_count = len(self._row_heights)
        items = list(self._row_heights.keys())
        self._scroll.set_items(items)

    def remove_message(self, message_id: str) -> None:
        """Remove a message from the list.

        Args:
            message_id: Identifier of message to remove.
        """
        if message_id not in self._row_heights:
            return
        del self._row_heights[message_id]
        self._state.message_count = len(self._row_heights)
        items = list(self._row_heights.keys())
        self._scroll.set_items(items)

    def update_message_height(self, message_id: str, height: int) -> None:
        """Update measured height for a message.

        Args:
            message_id: Identifier of the message.
            height: New measured height.
        """
        if message_id not in self._row_heights:
            return
        index = list(self._row_heights.keys()).index(message_id)
        self._row_heights[message_id] = height
        self._scroll.measure_item(index, height)

    def get_message_lines(self, message_id: str) -> int:
        """Get line count for a message.

        Args:
            message_id: Identifier of the message.

        Returns:
            Line count, or default estimate if not found.
        """
        return self._row_heights.get(message_id, VirtualScrollResult.DEFAULT_ESTIMATE)

    def scroll_to_index(self, index: int) -> int:
        """Get scroll position for message at index.

        Args:
            index: Message index.

        Returns:
            Scroll position.
        """
        return self._scroll.scroll_to_index(index)

    def compute_visible_range(
        self,
        viewport_top: int,
        viewport_height: int,
    ) -> tuple[int, int]:
        """Compute visible message range.

        Args:
            viewport_top: Top of viewport.
            viewport_height: Height of viewport.

        Returns:
            Tuple of (start_index, end_index).
        """
        return self._scroll.compute_range(viewport_top, viewport_height)

    def set_sticky_prompt(self, index: int) -> None:
        """Set sticky prompt index.

        Args:
            index: Index of sticky prompt, or -1 to clear.
        """
        self._state.set_sticky_prompt(index)

    def get_total_height(self) -> int:
        """Get total content height.

        Returns:
            Total rendered height.
        """
        return self._scroll.get_total_height()
