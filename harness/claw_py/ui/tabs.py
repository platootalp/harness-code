"""UI Tabs component for Claude Code TUI.

TypeScript equivalent: design-system/Tabs.tsx
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# =============================================================================
# Types
# =============================================================================


TabId = str | int
TabSelectCallback = Callable[[TabId], None]
TabCloseCallback = Callable[[TabId], None]


# =============================================================================
# Tabs Orientation
# =============================================================================


class TabsOrientation(StrEnum):
    """Orientation of the tabs."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


# =============================================================================
# Tab
# =============================================================================


@dataclass
class Tab:
    """A single tab.

    TypeScript equivalent: Tab component in Tabs.tsx

    Attributes:
        id: Unique identifier for the tab.
        label: Display label.
        is_active: Whether this tab is currently active.
        is_disabled: Whether this tab is disabled.
        badge: Optional badge/count to show.
        icon: Optional icon identifier.
    """

    id: TabId
    label: str
    is_active: bool = False
    is_disabled: bool = False
    badge: int | None = None
    icon: str | None = None

    def activate(self) -> None:
        """Activate this tab."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate this tab."""
        self.is_active = False

    def enable(self) -> None:
        """Enable this tab."""
        self.is_disabled = False

    def disable(self) -> None:
        """Disable this tab."""
        self.is_disabled = True


# =============================================================================
# Tabs Container
# =============================================================================


@dataclass
class Tabs:
    """Tabs container component.

    TypeScript equivalent: Tabs.tsx

    Attributes:
        tabs: List of tabs.
        orientation: Layout orientation.
    """

    tabs: list[Tab] = field(default_factory=list)
    orientation: TabsOrientation = TabsOrientation.HORIZONTAL
    _on_select: TabSelectCallback | None = field(default=None, repr=False)
    _on_close: TabCloseCallback | None = field(default=None, repr=False)
    _tab_map: dict[TabId, Tab] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Build tab lookup map."""
        self._tab_map = {tab.id: tab for tab in self.tabs}

    @property
    def tab_count(self) -> int:
        """Return number of tabs."""
        return len(self.tabs)

    @property
    def active_tab_id(self) -> TabId | None:
        """Return the active tab id."""
        for tab in self.tabs:
            if tab.is_active:
                return tab.id
        return None

    def get_tab(self, tab_id: TabId) -> Tab | None:
        """Get tab by id.

        Args:
            tab_id: Identifier of the tab.

        Returns:
            Tab or None if not found.
        """
        return self._tab_map.get(tab_id)

    def add_tab(
        self,
        id: TabId,
        label: str,
        badge: int | None = None,
        icon: str | None = None,
        is_active: bool = False,
        is_disabled: bool = False,
    ) -> None:
        """Add a new tab.

        Args:
            id: Unique identifier.
            label: Display label.
            badge: Optional badge count.
            icon: Optional icon.
            is_active: Whether this tab starts active.
            is_disabled: Whether this tab starts disabled.
        """
        if id in self._tab_map:
            return
        tab = Tab(id=id, label=label, badge=badge, icon=icon,
                  is_active=is_active, is_disabled=is_disabled)
        self.tabs.append(tab)
        self._tab_map[id] = tab

    def remove_tab(self, tab_id: TabId) -> None:
        """Remove a tab.

        Args:
            tab_id: Identifier of tab to remove.
        """
        if tab_id not in self._tab_map:
            return
        tab = self._tab_map[tab_id]
        self.tabs.remove(tab)
        del self._tab_map[tab_id]
        if tab.is_active:
            # Clear active if removed tab was active
            for t in self.tabs:
                if not t.is_disabled:
                    t.activate()
                    break

    def select_tab(self, tab_id: TabId) -> bool:
        """Select a tab.

        Args:
            tab_id: Identifier of tab to select.

        Returns:
            True if selection succeeded.
        """
        tab = self._tab_map.get(tab_id)
        if tab is None or tab.is_disabled:
            return False

        # Deactivate all tabs
        for t in self.tabs:
            t.deactivate()
        tab.activate()

        if self._on_select:
            self._on_select(tab_id)
        return True

    def select_by_index(self, index: int) -> bool:
        """Select tab by index.

        Args:
            index: Zero-based index.

        Returns:
            True if selection succeeded.
        """
        if 0 <= index < len(self.tabs):
            return self.select_tab(self.tabs[index].id)
        return False

    def select_first(self) -> bool:
        """Select the first enabled tab.

        Returns:
            True if selection succeeded.
        """
        enabled = self.get_enabled_tabs()
        if enabled:
            return self.select_tab(enabled[0].id)
        return False

    def select_last(self) -> bool:
        """Select the last enabled tab.

        Returns:
            True if selection succeeded.
        """
        enabled = self.get_enabled_tabs()
        if enabled:
            return self.select_tab(enabled[-1].id)
        return False

    def close_tab(self, tab_id: TabId) -> None:
        """Close (remove) a tab.

        Args:
            tab_id: Identifier of tab to close.
        """
        if self._on_close:
            self._on_close(tab_id)
        self.remove_tab(tab_id)

    def get_tab_order(self) -> list[Tab]:
        """Get tabs in display order.

        Returns:
            List of tabs in order.
        """
        return list(self.tabs)

    def get_enabled_tabs(self) -> list[Tab]:
        """Get only enabled tabs.

        Returns:
            List of enabled tabs in order.
        """
        return [t for t in self.tabs if not t.is_disabled]

    def select_next_enabled(self) -> bool:
        """Select the next enabled tab after the active one.

        Returns:
            True if selection succeeded.
        """
        enabled = self.get_enabled_tabs()
        if not enabled:
            return False
        current_id = self.active_tab_id
        if current_id is None:
            return self.select_tab(enabled[0].id)
        for i, tab in enumerate(enabled):
            if tab.id == current_id:
                next_idx = (i + 1) % len(enabled)
                return self.select_tab(enabled[next_idx].id)
        return self.select_tab(enabled[0].id)

    def select_previous_enabled(self) -> bool:
        """Select the previous enabled tab before the active one.

        Returns:
            True if selection succeeded.
        """
        enabled = self.get_enabled_tabs()
        if not enabled:
            return False
        current_id = self.active_tab_id
        if current_id is None:
            return self.select_tab(enabled[-1].id)
        for i, tab in enumerate(enabled):
            if tab.id == current_id:
                prev_idx = (i - 1) % len(enabled)
                return self.select_tab(enabled[prev_idx].id)
        return self.select_tab(enabled[-1].id)

    def update_tab_badge(self, tab_id: TabId, badge: int | None) -> None:
        """Update tab badge.

        Args:
            tab_id: Identifier of tab.
            badge: New badge value or None to clear.
        """
        tab = self._tab_map.get(tab_id)
        if tab:
            tab.badge = badge

    def set_on_select(self, callback: TabSelectCallback) -> None:
        """Set tab selection callback.

        Args:
            callback: Function called when a tab is selected.
        """
        self._on_select = callback

    def set_on_close(self, callback: TabCloseCallback) -> None:
        """Set tab close callback.

        Args:
            callback: Function called when a tab is closed.
        """
        self._on_close = callback
