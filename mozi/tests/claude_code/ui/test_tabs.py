"""Tests for UI tabs components."""

from __future__ import annotations

import pytest

from claude_code.ui.tabs import (
    Tab,
    TabId,
    Tabs,
    TabsOrientation,
)


class TestTabsOrientation:
    """Tests for TabsOrientation enum."""

    def test_values(self) -> None:
        """TabsOrientation has expected values."""
        assert TabsOrientation.HORIZONTAL == "horizontal"
        assert TabsOrientation.VERTICAL == "vertical"


class TestTab:
    """Tests for Tab."""

    def test_default_values(self) -> None:
        """Tab has correct defaults."""
        tab = Tab(id="tab-1", label="Tab 1")
        assert tab.id == "tab-1"
        assert tab.label == "Tab 1"
        assert tab.is_active is False
        assert tab.is_disabled is False
        assert tab.badge is None
        assert tab.icon is None

    def test_activate_deactivate(self) -> None:
        """activate and deactivate work."""
        tab = Tab(id="tab-1", label="Tab 1")
        tab.activate()
        assert tab.is_active is True
        tab.deactivate()
        assert tab.is_active is False

    def test_enable_disable(self) -> None:
        """enable and disable work."""
        tab = Tab(id="tab-1", label="Tab 1")
        tab.disable()
        assert tab.is_disabled is True
        tab.enable()
        assert tab.is_disabled is False

    def test_with_badge(self) -> None:
        """Badge can be set."""
        tab = Tab(id="tab-1", label="Tab 1", badge=5)
        assert tab.badge == 5


class TestTabs:
    """Tests for Tabs container."""

    def test_empty_tabs(self) -> None:
        """Empty Tabs has correct defaults."""
        tabs = Tabs()
        assert tabs.tab_count == 0
        assert tabs.active_tab_id is None
        assert tabs.orientation == TabsOrientation.HORIZONTAL

    def test_add_tab(self) -> None:
        """add_tab works correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        assert tabs.tab_count == 1
        found = tabs.get_tab("tab-1")
        assert found is not None
        assert found.label == "Tab 1"

    def test_add_duplicate_tab(self) -> None:
        """Duplicate tabs are ignored."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-1", label="Tab 1 Alt")
        assert tabs.tab_count == 1
        found = tabs.get_tab("tab-1")
        assert found is not None
        assert found.label == "Tab 1"

    def test_remove_tab(self) -> None:
        """remove_tab works correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        tabs.remove_tab("tab-1")
        assert tabs.tab_count == 1
        assert tabs.get_tab("tab-1") is None
        assert tabs.get_tab("tab-2") is not None

    def test_remove_nonexistent_tab(self) -> None:
        """Removing nonexistent tab is safe."""
        tabs = Tabs()
        tabs.remove_tab("tab-1")
        assert tabs.tab_count == 0

    def test_select_tab(self) -> None:
        """select_tab works correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        result = tabs.select_tab("tab-1")
        assert result is True
        assert tabs.active_tab_id == "tab-1"
        tab1 = tabs.get_tab("tab-1")
        assert tab1 is not None
        assert tab1.is_active is True
        tab2 = tabs.get_tab("tab-2")
        assert tab2 is not None
        assert tab2.is_active is False

    def test_select_disabled_tab(self) -> None:
        """Cannot select disabled tab."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1", is_disabled=True)
        result = tabs.select_tab("tab-1")
        assert result is False

    def test_select_nonexistent_tab(self) -> None:
        """Selecting nonexistent tab returns False."""
        tabs = Tabs()
        result = tabs.select_tab("tab-1")
        assert result is False

    def test_select_tab_by_index(self) -> None:
        """select_by_index works correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        result = tabs.select_by_index(1)
        assert result is True
        assert tabs.active_tab_id == "tab-2"

    def test_select_first(self) -> None:
        """select_first works correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2", is_disabled=True)
        result = tabs.select_first()
        assert result is True
        assert tabs.active_tab_id == "tab-1"

    def test_select_first_empty(self) -> None:
        """select_first returns False on empty tabs."""
        tabs = Tabs()
        result = tabs.select_first()
        assert result is False

    def test_select_last(self) -> None:
        """select_last works correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1", is_disabled=True)
        tabs.add_tab(id="tab-2", label="Tab 2")
        result = tabs.select_last()
        assert result is True
        assert tabs.active_tab_id == "tab-2"

    def test_select_next_enabled(self) -> None:
        """select_next_enabled cycles correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        tabs.add_tab(id="tab-3", label="Tab 3")
        tabs.select_tab("tab-1")

        tabs.select_next_enabled()
        assert tabs.active_tab_id == "tab-2"
        tabs.select_next_enabled()
        assert tabs.active_tab_id == "tab-3"
        tabs.select_next_enabled()
        assert tabs.active_tab_id == "tab-1"  # Wraps around

    def test_select_next_enabled_disabled_in_middle(self) -> None:
        """select_next_enabled skips disabled tabs."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2", is_disabled=True)
        tabs.add_tab(id="tab-3", label="Tab 3")
        tabs.select_tab("tab-1")
        tabs.select_next_enabled()
        assert tabs.active_tab_id == "tab-3"

    def test_select_previous_enabled(self) -> None:
        """select_previous_enabled cycles correctly."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        tabs.select_tab("tab-2")
        tabs.select_previous_enabled()
        assert tabs.active_tab_id == "tab-1"
        tabs.select_previous_enabled()
        assert tabs.active_tab_id == "tab-2"  # Wraps around

    def test_close_tab(self) -> None:
        """close_tab calls callback and removes."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        closed: list[TabId] = []

        def on_close(tab_id: TabId) -> None:
            closed.append(tab_id)

        tabs.set_on_close(on_close)
        tabs.close_tab("tab-1")
        assert closed == ["tab-1"]
        assert tabs.tab_count == 0

    def test_get_tab_order(self) -> None:
        """get_tab_order returns tabs in order."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        order = tabs.get_tab_order()
        assert len(order) == 2
        assert order[0].id == "tab-1"
        assert order[1].id == "tab-2"

    def test_get_enabled_tabs(self) -> None:
        """get_enabled_tabs returns only enabled."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2", is_disabled=True)
        tabs.add_tab(id="tab-3", label="Tab 3")
        enabled = tabs.get_enabled_tabs()
        assert len(enabled) == 2
        assert enabled[0].id == "tab-1"
        assert enabled[1].id == "tab-3"

    def test_update_tab_badge(self) -> None:
        """update_tab_badge works."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.update_tab_badge("tab-1", 5)
        tab = tabs.get_tab("tab-1")
        assert tab is not None
        assert tab.badge == 5
        tabs.update_tab_badge("tab-1", None)
        tab = tabs.get_tab("tab-1")
        assert tab is not None
        assert tab.badge is None

    def test_remove_active_tab_selects_first(self) -> None:
        """Removing active tab selects first enabled."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        tabs.add_tab(id="tab-2", label="Tab 2")
        tabs.select_tab("tab-1")
        tabs.remove_tab("tab-1")
        assert tabs.active_tab_id == "tab-2"

    def test_callback_on_select(self) -> None:
        """on_select callback is called."""
        tabs = Tabs()
        tabs.add_tab(id="tab-1", label="Tab 1")
        selected: list[TabId] = []

        def on_select(tab_id: TabId) -> None:
            selected.append(tab_id)

        tabs.set_on_select(on_select)
        tabs.select_tab("tab-1")
        assert selected == ["tab-1"]
