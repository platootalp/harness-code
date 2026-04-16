"""Tests for UI base widgets (Widget, Box, Pane, Dialog, Text)."""

from __future__ import annotations

import pytest

from claude_code.ui.base_widgets import (
    Box,
    BoxOrientation,
    Dialog,
    DialogPosition,
    Pane,
    PaneBorderStyle,
    Text,
    TextStyle,
    Widget,
    WidgetAlign,
    WidgetDisplay,
)


class TestWidget:
    """Tests for the base Widget class."""

    def test_default_values(self) -> None:
        """Widget has correct default values."""
        widget = Widget()
        assert widget.id == ""
        assert widget.is_visible is True
        assert widget.is_focused is False
        assert widget.is_disabled is False
        assert widget.display == WidgetDisplay.FLEX
        assert widget.align == WidgetAlign.START
        assert widget.children == []

    def test_show_hide(self) -> None:
        """Show and hide work correctly."""
        widget = Widget()
        widget.hide()
        assert widget.is_visible is False
        widget.show()
        assert widget.is_visible is True

    def test_focus_blur(self) -> None:
        """Focus and blur work correctly."""
        widget = Widget()
        widget.focus()
        assert widget.is_focused is True
        widget.blur()
        assert widget.is_focused is False

    def test_enable_disable(self) -> None:
        """Enable and disable work correctly."""
        widget = Widget()
        widget.disable()
        assert widget.is_disabled is True
        widget.enable()
        assert widget.is_disabled is False

    def test_add_child(self) -> None:
        """Adding children works."""
        parent = Widget()
        child = Widget(id="child1")
        parent.add_child(child)
        assert child in parent.children
        assert len(parent.children) == 1

    def test_remove_child(self) -> None:
        """Removing children works."""
        parent = Widget()
        child = Widget(id="child1")
        parent.add_child(child)
        parent.remove_child(child)
        assert child not in parent.children
        assert len(parent.children) == 0

    def test_clear_children(self) -> None:
        """Clearing children works."""
        parent = Widget()
        parent.add_child(Widget())
        parent.add_child(Widget())
        assert len(parent.children) == 2
        parent.clear_children()
        assert len(parent.children) == 0

    def test_children_returns_list(self) -> None:
        """Children property returns the internal list."""
        parent = Widget()
        children = parent.children
        children.append(Widget())
        # Note: children property returns the actual internal list
        assert len(parent.children) == 1


class TestText:
    """Tests for the Text widget."""

    def test_default_values(self) -> None:
        """Text has correct defaults."""
        text = Text(content="Hello")
        assert text.content == "Hello"
        assert text.text_style == TextStyle.NORMAL
        assert text.is_truncated is False
        assert text.max_lines is None
        assert text.truncated_at is None

    def test_truncate(self) -> None:
        """Truncation works correctly."""
        text = Text(content="Hello", max_lines=10)
        text.truncate(at_line=5)
        assert text.is_truncated is True
        assert text.truncated_at == 5

    def test_truncate_without_max_lines(self) -> None:
        """Truncation requires max_lines to be set."""
        text = Text(content="Hello")
        text.truncate(at_line=5)
        # truncate sets is_truncated only when max_lines is set
        assert text.is_truncated is False


class TestBox:
    """Tests for the Box widget."""

    def test_default_values(self) -> None:
        """Box has correct defaults."""
        box = Box()
        assert box.orientation == BoxOrientation.VERTICAL
        assert box.gap == 0
        assert box.children == []

    def test_orientation(self) -> None:
        """Orientation can be changed."""
        box = Box(orientation=BoxOrientation.HORIZONTAL)
        assert box.orientation == BoxOrientation.HORIZONTAL

    def test_gap(self) -> None:
        """Gap can be set."""
        box = Box(gap=8)
        assert box.gap == 8

    def test_add_remove_children(self) -> None:
        """Box supports child management."""
        box = Box()
        child1 = Widget(id="w1")
        child2 = Widget(id="w2")
        box.add_child(child1)
        box.add_child(child2)
        assert len(box.children) == 2
        box.remove_child(child1)
        assert len(box.children) == 1


class TestPane:
    """Tests for the Pane widget."""

    def test_default_values(self) -> None:
        """Pane has correct defaults."""
        pane = Pane()
        assert pane.title == ""
        assert pane.border_style == PaneBorderStyle.SINGLE
        assert pane.border_color is None
        assert pane.has_header is True
        assert pane.has_footer is False

    def test_with_title(self) -> None:
        """Pane can have a title."""
        pane = Pane(title="My Pane")
        assert pane.title == "My Pane"

    def test_border_styles(self) -> None:
        """Different border styles work."""
        for style in PaneBorderStyle:
            pane = Pane(border_style=style)
            assert pane.border_style == style

    def test_add_remove_children(self) -> None:
        """Pane supports child management."""
        pane = Pane()
        pane.add_child(Widget())
        assert len(pane.children) == 1
        pane.clear_children()
        assert len(pane.children) == 0


class TestDialog:
    """Tests for the Dialog widget."""

    def test_default_values(self) -> None:
        """Dialog has correct defaults."""
        dialog = Dialog()
        assert dialog.title == ""
        assert dialog.subtitle is None
        assert dialog.is_cancelable is True
        assert dialog.is_closeable is True
        assert dialog.position == DialogPosition.CENTER
        assert dialog.has_input_guide is True

    def test_with_title(self) -> None:
        """Dialog can have a title and subtitle."""
        dialog = Dialog(title="Confirm", subtitle="Are you sure?")
        assert dialog.title == "Confirm"
        assert dialog.subtitle == "Are you sure?"

    def test_hide_show_input_guide(self) -> None:
        """Input guide visibility can be toggled."""
        dialog = Dialog()
        dialog.hide_input_guide()
        assert dialog.has_input_guide is False
        dialog.show_input_guide()
        assert dialog.has_input_guide is True

    def test_positions(self) -> None:
        """Different positions work."""
        for pos in DialogPosition:
            dialog = Dialog(position=pos)
            assert dialog.position == pos
