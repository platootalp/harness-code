"""
Tests for UI Tabs component.
"""

from __future__ import annotations

import pytest

from claude_code.ui.tabs import (
    Tab,
    TabCloseCallback,
    TabId,
    TabSelectCallback,
    Tabs,
    TabsOrientation,
)


class TestTabId:
    """Tests for TabId type."""

    def test_tab_id_string(self) -> None:
        """Test TabId can be a string."""
        tid: TabId = "tab-1"
        assert tid == "tab-1"

    def test_tab_id_int(self) -> None:
        """Test TabId can be an int."""
        tid: TabId = 42
        assert tid == 42


class TestTab:
    """Tests for Tab dataclass."""

    def test_create(self) -> None:
        """Test creating a tab."""
        tab = Tab(id="tab-1", label="Messages")
        assert tab.id == "tab-1"
        assert tab.label == "Messages"
        assert tab.is_active is False
        assert tab.is_disabled is False
        assert tab.badge is None
        assert tab.icon is None

    def test_create_with_all_fields(self) -> None:
        """Test creating tab with all fields."""
        tab = Tab(
            id="tab-1",
            label="Messages",
            is_active=True,
            is_disabled=True,
            badge=5,
            icon="inbox",
        )
        assert tab.is_active is True
        assert tab.is_disabled is True
        assert tab.badge == 5
        assert tab.icon == "inbox"

    def test_activate(self) -> None:
        """Test activating a tab."""
        tab = Tab(id="tab-1", label="Messages")
        assert tab.is_active is False
        tab.activate()
        assert tab.is_active is True

    def test_deactivate(self) -> None:
        """Test deactivating a tab."""
        tab = Tab(id="tab-1", label="Messages", is_active=True)
        tab.deactivate()
        assert tab.is_active is False

    def test_enable(self) -> None:
        """Test enabling a tab."""
        tab = Tab(id="tab-1", label="Messages", is_disabled=True)
        tab.enable()
        assert tab.is_disabled is False

    def test_disable(self) -> None:
        """Test disabling a tab."""
        tab = Tab(id="tab-1", label="Messages")
        tab.disable()
        assert tab.is_disabled is True


class TestTabsOrientation:
    """Tests for TabsOrientation enum."""

    def test_values(self) -> None:
        """Test orientation values."""
        assert TabsOrientation.HORIZONTAL.value == "horizontal"
        assert TabsOrientation.VERTICAL.value == "vertical"

    def test_is_string(self) -> None:
        """Test orientation is a string enum."""
        assert isinstance(TabsOrientation.HORIZONTAL, str)


class TestTabs:
    """Tests for Tabs container."""

    def test_create_empty(self) -> None:
        """Test creating empty tabs container."""
        tabs = Tabs()
        assert tabs.tab_count == 0
        assert tabs.active_tab_id is None
        assert tabs.orientation == TabsOrientation.HORIZONTAL

    def test_create_with_tabs(self) -> None:
        """Test creating tabs with initial tabs."""
        tabs = Tabs(
            tabs=[
                Tab(id="tab-1", label="Messages"),
                Tab(id="tab-2", label="Tasks"),
            ],
        )
        assert tabs.tab_count == 2
        assert tabs.active_tab_id is None

    def test_create_with_active_tab(self) -> None:
        """Test creating tabs with active tab."""
        tabs = Tabs(
            tabs=[
                Tab(id="tab-1", label="Messages"),
                Tab(id="tab-2", label="Tasks", is_active=True),
            ],
        )
        assert tabs.active_tab_id == "tab-2"

    def test_create_vertical(self) -> None:
        """Test creating vertical tabs."""
        tabs = Tabs(orientation=TabsOrientation.VERTICAL)
        assert tabs.orientation == TabsOrientation.VERTICAL

    def test_add_tab(self) -> None:
        """Test adding a tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        assert tabs.tab_count == 1
        assert tabs.get_tab("tab-1") is not None
        assert tabs.get_tab("tab-1").label == "Messages"

    def test_add_tab_with_badge(self) -> None:
        """Test adding tab with badge."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages", badge=5)
        assert tabs.get_tab("tab-1").badge == 5

    def test_remove_tab(self) -> None:
        """Test removing a tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks")
        assert tabs.tab_count == 2
        tabs.remove_tab("tab-1")
        assert tabs.tab_count == 1
        assert tabs.get_tab("tab-1") is None

    def test_remove_active_tab(self) -> None:
        """Test removing active tab clears active_tab_id."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages", is_active=True)
        assert tabs.active_tab_id == "tab-1"
        tabs.remove_tab("tab-1")
        assert tabs.active_tab_id is None

    def test_remove_nonexistent_tab(self) -> None:
        """Test removing nonexistent tab does not error."""
        tabs = Tabs()
        tabs.remove_tab("nonexistent")  # Should not raise
        assert tabs.tab_count == 0

    def test_select_tab(self) -> None:
        """Test selecting a tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks")
        tabs.select_tab("tab-2")
        assert tabs.active_tab_id == "tab-2"
        assert tabs.get_tab("tab-1").is_active is False
        assert tabs.get_tab("tab-2").is_active is True

    def test_select_triggers_callback(self) -> None:
        """Test selecting tab triggers callback."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks")
        selected: list[TabId] = []

        def on_select(tab_id: TabId) -> None:
            selected.append(tab_id)

        tabs.set_on_select(on_select)
        tabs.select_tab("tab-2")
        assert selected == ["tab-2"]

    def test_select_disabled_tab_does_not_activate(self) -> None:
        """Test selecting disabled tab does not activate it."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks", is_disabled=True)
        tabs.select_tab("tab-2")
        # Disabled tab should not become active
        assert tabs.get_tab("tab-2").is_active is False
        assert tabs.active_tab_id != "tab-2"

    def test_get_tab_order(self) -> None:
        """Test getting tabs in order."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="First")
        tabs.add_tab(id="tab-2", label="Second")
        tabs.add_tab(id="tab-3", label="Third")
        order = tabs.get_tab_order()
        assert [t.id for t in order] == ["tab-1", "tab-2", "tab-3"]

    def test_select_by_index(self) -> None:
        """Test selecting tab by index."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks")
        tabs.add_tab(id="tab-3", label="Settings")
        tabs.select_by_index(2)
        assert tabs.active_tab_id == "tab-3"

    def test_select_first(self) -> None:
        """Test selecting first tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks")
        tabs.select_first()
        assert tabs.active_tab_id == "tab-1"

    def test_select_last(self) -> None:
        """Test selecting last tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks")
        tabs.select_last()
        assert tabs.active_tab_id == "tab-2"

    def test_select_empty_does_not_error(self) -> None:
        """Test selecting on empty tabs does not error."""
        tabs = Tabs()
        tabs.select_tab("nonexistent")  # Should not raise
        assert tabs.active_tab_id is None

    def test_close_callback(self) -> None:
        """Test close callback is called."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        closed: list[TabId] = []

        def on_close(tab_id: TabId) -> None:
            closed.append(tab_id)

        tabs.set_on_close(on_close)
        tabs.close_tab("tab-1")
        assert closed == ["tab-1"]
        assert tabs.tab_count == 0

    def test_get_enabled_tabs(self) -> None:
        """Test getting enabled tabs only."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks", is_disabled=True)
        tabs.add_tab(id="tab-3", label="Settings")
        enabled = tabs.get_enabled_tabs()
        assert len(enabled) == 2
        assert enabled[0].id == "tab-1"
        assert enabled[1].id == "tab-3"

    def test_select_next_enabled(self) -> None:
        """Test selecting next enabled tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks", is_disabled=True)
        tabs.add_tab(id="tab-3", label="Settings")
        tabs.select_tab("tab-1")
        tabs.select_next_enabled()
        assert tabs.active_tab_id == "tab-3"

    def test_select_previous_enabled(self) -> None:
        """Test selecting previous enabled tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.add_tab(id="tab-2", label="Tasks", is_disabled=True)
        tabs.add_tab(id="tab-3", label="Settings")
        tabs.select_tab("tab-3")
        tabs.select_previous_enabled()
        assert tabs.active_tab_id == "tab-1"

    def test_update_tab_badge(self) -> None:
        """Test updating tab badge."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages")
        tabs.update_tab_badge("tab-1", 10)
        assert tabs.get_tab("tab-1").badge == 10

    def test_clear_badge(self) -> None:
        """Test clearing tab badge."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Messages", badge=5)
        tabs.update_tab_badge("tab-1", None)
        assert tabs.get_tab("tab-1").badge is None
