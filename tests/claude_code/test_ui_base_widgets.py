"""
Tests for UI base widget components.
"""

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


# =============================================================================
# Widget Tests
# =============================================================================


class TestWidget:
    """Tests for Widget base class."""

    def test_create(self) -> None:
        """Test creating a widget."""
        w = Widget(id="widget-1")
        assert w.id == "widget-1"
        assert w.is_visible is True
        assert w.is_focused is False
        assert w.is_disabled is False
        assert w.display == WidgetDisplay.FLEX
        assert w.align == WidgetAlign.START

    def test_create_with_style(self) -> None:
        """Test creating widget with styling."""
        w = Widget(id="widget-1", is_visible=False, is_disabled=True)
        assert w.is_visible is False
        assert w.is_disabled is True

    def test_show_hide(self) -> None:
        """Test show/hide."""
        w = Widget()
        w.hide()
        assert w.is_visible is False
        w.show()
        assert w.is_visible is True

    def test_enable_disable(self) -> None:
        """Test enable/disable."""
        w = Widget()
        w.disable()
        assert w.is_disabled is True
        w.enable()
        assert w.is_disabled is False

    def test_focus(self) -> None:
        """Test focus."""
        w = Widget()
        w.focus()
        assert w.is_focused is True
        w.blur()
        assert w.is_focused is False


class TestTextStyle:
    """Tests for TextStyle enum."""

    def test_values(self) -> None:
        """Test text style values."""
        assert TextStyle.NORMAL.value == "normal"
        assert TextStyle.BOLD.value == "bold"
        assert TextStyle.ITALIC.value == "italic"
        assert TextStyle.UNDERLINE.value == "underline"
        assert TextStyle.STRIKETHROUGH.value == "strikethrough"
        assert TextStyle.INVERSE.value == "inverse"


class TestText:
    """Tests for Text widget."""

    def test_create(self) -> None:
        """Test creating text."""
        t = Text(content="Hello world")
        assert t.content == "Hello world"
        assert t.text_style == TextStyle.NORMAL
        assert t.is_truncated is False
        assert t.max_lines is None

    def test_create_with_style(self) -> None:
        """Test creating styled text."""
        t = Text(content="Important", text_style=TextStyle.BOLD)
        assert t.text_style == TextStyle.BOLD

    def test_with_max_lines(self) -> None:
        """Test text with max lines."""
        t = Text(content="Long content", max_lines=2)
        assert t.max_lines == 2
        assert t.is_truncated is False
        t.truncate(1)
        assert t.is_truncated is True

    def test_truncate(self) -> None:
        """Test truncation."""
        t = Text(content="Hello world", max_lines=1)
        t.truncate(1)
        assert t.is_truncated is True
        assert t.truncated_at == 1


class TestBoxOrientation:
    """Tests for BoxOrientation enum."""

    def test_values(self) -> None:
        """Test orientation values."""
        assert BoxOrientation.HORIZONTAL.value == "horizontal"
        assert BoxOrientation.VERTICAL.value == "vertical"


class TestWidgetAlign:
    """Tests for WidgetAlign enum."""

    def test_values(self) -> None:
        """Test align values."""
        assert WidgetAlign.START.value == "start"
        assert WidgetAlign.CENTER.value == "center"
        assert WidgetAlign.END.value == "end"
        assert WidgetAlign.STRETCH.value == "stretch"


class TestWidgetDisplay:
    """Tests for WidgetDisplay enum."""

    def test_values(self) -> None:
        """Test display values."""
        assert WidgetDisplay.FLEX.value == "flex"
        assert WidgetDisplay.NONE.value == "none"
        assert WidgetDisplay.INLINE.value == "inline"


class TestBox:
    """Tests for Box widget."""

    def test_create(self) -> None:
        """Test creating box."""
        b = Box(orientation=BoxOrientation.VERTICAL)
        assert b.orientation == BoxOrientation.VERTICAL
        assert b.gap == 0
        assert b.children == []

    def test_create_horizontal(self) -> None:
        """Test creating horizontal box."""
        b = Box(orientation=BoxOrientation.HORIZONTAL)
        assert b.orientation == BoxOrientation.HORIZONTAL

    def test_with_gap(self) -> None:
        """Test box with gap."""
        b = Box(orientation=BoxOrientation.VERTICAL, gap=2)
        assert b.gap == 2

    def test_add_child(self) -> None:
        """Test adding child widgets."""
        b = Box()
        child = Text(content="Hello")
        b.add_child(child)
        assert len(b.children) == 1
        assert b.children[0] is child

    def test_remove_child(self) -> None:
        """Test removing child widgets."""
        b = Box()
        child = Text(content="Hello")
        b.add_child(child)
        b.remove_child(child)
        assert len(b.children) == 0

    def test_clear_children(self) -> None:
        """Test clearing all children."""
        b = Box()
        b.add_child(Text(content="a"))
        b.add_child(Text(content="b"))
        b.clear_children()
        assert len(b.children) == 0


class TestPaneBorderStyle:
    """Tests for PaneBorderStyle enum."""

    def test_values(self) -> None:
        """Test border style values."""
        assert PaneBorderStyle.SINGLE.value == "single"
        assert PaneBorderStyle.DOUBLE.value == "double"
        assert PaneBorderStyle.ROUNDED.value == "rounded"
        assert PaneBorderStyle.NONE.value == "none"


class TestPane:
    """Tests for Pane widget."""

    def test_create(self) -> None:
        """Test creating pane."""
        p = Pane(title="My Pane")
        assert p.title == "My Pane"
        assert p.border_style == PaneBorderStyle.SINGLE
        assert p.border_color is None
        assert p.has_footer is False
        assert p.has_header is True

    def test_create_with_border(self) -> None:
        """Test creating pane with border style."""
        p = Pane(title="Dialog", border_style=PaneBorderStyle.DOUBLE)
        assert p.border_style == PaneBorderStyle.DOUBLE

    def test_create_with_color(self) -> None:
        """Test creating pane with border color."""
        p = Pane(title="Error", border_color="#f85149")
        assert p.border_color == "#f85149"

    def test_with_children(self) -> None:
        """Test pane with children."""
        p = Pane(title="Container")
        inner = Box()
        p.add_child(inner)
        assert len(p.children) == 1

    def test_show_footer(self) -> None:
        """Test showing footer."""
        p = Pane(title="With Footer", has_footer=True)
        assert p.has_footer is True


class TestDialogPosition:
    """Tests for DialogPosition enum."""

    def test_values(self) -> None:
        """Test position values."""
        assert DialogPosition.CENTER.value == "center"
        assert DialogPosition.TOP.value == "top"
        assert DialogPosition.BOTTOM.value == "bottom"
        assert DialogPosition.FULL.value == "full"


class TestDialog:
    """Tests for Dialog widget."""

    def test_create(self) -> None:
        """Test creating dialog."""
        d = Dialog(title="Confirm Action")
        assert d.title == "Confirm Action"
        assert d.subtitle is None
        assert d.is_cancelable is True
        assert d.is_closeable is True
        assert d.position == DialogPosition.CENTER
        assert d.has_input_guide is True

    def test_create_with_subtitle(self) -> None:
        """Test dialog with subtitle."""
        d = Dialog(title="Warning", subtitle="This action cannot be undone")
        assert d.subtitle == "This action cannot be undone"

    def test_create_non_cancelable(self) -> None:
        """Test non-cancelable dialog."""
        d = Dialog(title="Critical", is_cancelable=False)
        assert d.is_cancelable is False

    def test_create_fullscreen(self) -> None:
        """Test fullscreen dialog."""
        d = Dialog(title="Full", position=DialogPosition.FULL)
        assert d.position == DialogPosition.FULL

    def test_with_content(self) -> None:
        """Test dialog with content."""
        d = Dialog(title="Content Dialog")
        box = Box()
        d.add_child(box)
        assert len(d.children) == 1

    def test_show_input_guide(self) -> None:
        """Test input guide visibility."""
        d = Dialog(title="With Guide", has_input_guide=True)
        assert d.has_input_guide is True
        d.hide_input_guide()
        assert d.has_input_guide is False

    def test_non_closeable(self) -> None:
        """Test non-closeable dialog."""
        d = Dialog(title="Strict", is_closeable=False)
        assert d.is_closeable is False
