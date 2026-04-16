"""UI base widget components for Claude Code TUI.

TypeScript equivalent: design-system/Box.tsx, Pane.tsx, Dialog.tsx, Text.tsx
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Enums
# =============================================================================


class TextStyle(StrEnum):
    """Text styling options."""

    NORMAL = "normal"
    BOLD = "bold"
    ITALIC = "italic"
    UNDERLINE = "underline"
    STRIKETHROUGH = "strikethrough"
    INVERSE = "inverse"


class BoxOrientation(StrEnum):
    """Box layout orientation."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class WidgetAlign(StrEnum):
    """Widget alignment options."""

    START = "start"
    CENTER = "center"
    END = "end"
    STRETCH = "stretch"


class WidgetDisplay(StrEnum):
    """Widget display options."""

    FLEX = "flex"
    NONE = "none"
    INLINE = "inline"


class PaneBorderStyle(StrEnum):
    """Pane border styles."""

    SINGLE = "single"
    DOUBLE = "double"
    ROUNDED = "rounded"
    NONE = "none"


class DialogPosition(StrEnum):
    """Dialog positioning."""

    CENTER = "center"
    TOP = "top"
    BOTTOM = "bottom"
    FULL = "full"


# =============================================================================
# Widget
# =============================================================================


@dataclass
class Widget:
    """Base widget class.

    TypeScript equivalent: Base widget component.

    Attributes:
        id: Unique identifier for the widget.
        is_visible: Whether the widget is visible.
        is_focused: Whether the widget has focus.
        is_disabled: Whether the widget is disabled.
        display: Display type.
        align: Alignment.
    """

    id: str = ""
    is_visible: bool = True
    is_focused: bool = False
    is_disabled: bool = False
    display: WidgetDisplay = WidgetDisplay.FLEX
    align: WidgetAlign = WidgetAlign.START
    _children: list[Widget] = field(default_factory=list, repr=False)

    def show(self) -> None:
        """Show the widget."""
        self.is_visible = True

    def hide(self) -> None:
        """Hide the widget."""
        self.is_visible = False

    def focus(self) -> None:
        """Focus the widget."""
        self.is_focused = True

    def blur(self) -> None:
        """Remove focus from the widget."""
        self.is_focused = False

    def enable(self) -> None:
        """Enable the widget."""
        self.is_disabled = False

    def disable(self) -> None:
        """Disable the widget."""
        self.is_disabled = True

    @property
    def children(self) -> list[Widget]:
        """Return child widgets."""
        return self._children

    def add_child(self, child: Widget) -> None:
        """Add a child widget.

        Args:
            child: Widget to add.
        """
        self._children.append(child)

    def remove_child(self, child: Widget) -> None:
        """Remove a child widget.

        Args:
            child: Widget to remove.
        """
        self._children.remove(child)

    def clear_children(self) -> None:
        """Remove all children."""
        self._children.clear()


# =============================================================================
# Text
# =============================================================================


@dataclass
class Text:
    """Text widget.

    TypeScript equivalent: Text component.

    Attributes:
        content: The text content.
        text_style: Text styling.
        is_truncated: Whether text is truncated.
        max_lines: Maximum lines before truncation.
        truncated_at: Line at which truncation occurred.
    """

    content: str
    text_style: TextStyle = TextStyle.NORMAL
    is_truncated: bool = False
    max_lines: int | None = None
    truncated_at: int | None = None

    def truncate(self, at_line: int) -> None:
        """Truncate text.

        Args:
            at_line: Line number to truncate at.
        """
        if self.max_lines is not None:
            self.is_truncated = True
            self.truncated_at = at_line


# =============================================================================
# Box
# =============================================================================


@dataclass
class Box(Widget):
    """Box widget (flex container).

    TypeScript equivalent: Box component.

    Attributes:
        orientation: Layout orientation.
        gap: Gap between children.
    """

    orientation: BoxOrientation = BoxOrientation.VERTICAL
    gap: int = 0

    def add_child(self, child: Widget) -> None:
        """Add a child widget."""
        self._children.append(child)

    def remove_child(self, child: Widget) -> None:
        """Remove a child widget."""
        self._children.remove(child)

    def clear_children(self) -> None:
        """Remove all children."""
        self._children.clear()


# =============================================================================
# Pane
# =============================================================================


@dataclass
class Pane(Widget):
    """Pane widget (bordered container).

    TypeScript equivalent: Pane component.

    Attributes:
        title: Pane title.
        border_style: Border style.
        border_color: Border color.
        has_header: Whether to show header.
        has_footer: Whether to show footer.
    """

    title: str = ""
    border_style: PaneBorderStyle = PaneBorderStyle.SINGLE
    border_color: str | None = None
    has_header: bool = True
    has_footer: bool = False

    def add_child(self, child: Widget) -> None:
        """Add a child widget."""
        self._children.append(child)

    def remove_child(self, child: Widget) -> None:
        """Remove a child widget."""
        self._children.remove(child)

    def clear_children(self) -> None:
        """Remove all children."""
        self._children.clear()


# =============================================================================
# Dialog
# =============================================================================


@dataclass
class Dialog(Widget):
    """Dialog widget.

    TypeScript equivalent: Dialog component.

    Attributes:
        title: Dialog title.
        subtitle: Optional subtitle.
        is_cancelable: Whether dialog can be cancelled.
        is_closeable: Whether dialog can be closed.
        position: Dialog position.
        has_input_guide: Whether to show keyboard hints.
    """

    title: str = ""
    subtitle: str | None = None
    is_cancelable: bool = True
    is_closeable: bool = True
    position: DialogPosition = DialogPosition.CENTER
    has_input_guide: bool = True

    def hide_input_guide(self) -> None:
        """Hide the input guide."""
        self.has_input_guide = False

    def show_input_guide(self) -> None:
        """Show the input guide."""
        self.has_input_guide = True

    def add_child(self, child: Widget) -> None:
        """Add a child widget."""
        self._children.append(child)

    def remove_child(self, child: Widget) -> None:
        """Remove a child widget."""
        self._children.remove(child)

    def clear_children(self) -> None:
        """Remove all children."""
        self._children.clear()
