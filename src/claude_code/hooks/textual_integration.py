"""
Textual Integration - Component state subscription for Textual apps.

Provides integration between the AppStateStore and Textual components,
enabling reactive state binding and lifecycle management.

Migrated from src/hooks/useTextualBinding.ts pattern.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app_state_store import AppStateStore
    from .change_record import ChangeRecord


@dataclass
class StateSubscription:
    """
    Manages a component's subscription to the app state store.

    Automatically subscribes on mount and unsubscribes on cleanup.
    Supports both global change subscriptions and key-specific subscriptions.
    """

    store: AppStateStore
    on_change: Callable[[], None]
    keys: list[str] = field(default_factory=list)
    _unsubs: list[Callable[[], None]] = field(default_factory=list, repr=False)
    _key_cache: dict[str, Any] = field(default_factory=dict)
    _render_version: int = field(default=-1)
    _render_count: int = field(default=-1)

    def attach(self) -> None:
        """
        Subscribe to the store and call on_change with initial state.

        Should be called in the component's on_mount handler.
        """
        if self.keys:
            # Populate cache with initial values BEFORE subscribing
            current_state = self.store.get()
            for key in self.keys:
                self._key_cache[key] = current_state.get(key)
            # Subscribe to all keys
            for key in self.keys:
                unsub = self.store.subscribe_to_key(
                    key,
                    lambda record, ver, key=key: self._handle_key_change(record, ver),
                )
                self._unsubs.append(unsub)
            # Always render once on initial attach to show the component
            self._render_count += 1
            self._render_version = self._render_count
            self.on_change()
        else:
            # Global subscription - call on_change immediately
            self._render_count += 1
            self._render_version = self._render_count
            self.on_change()

            def wrapped_listener(_version: int | None = None) -> None:
                """Called by store with optional version; we increment render count."""
                self._render_count += 1
                self._render_version = self._render_count
                self.on_change()

            unsub = self.store.subscribe(wrapped_listener)
            self._unsubs.append(unsub)

    def _handle_key_change(
        self, record: ChangeRecord, version: int
    ) -> None:
        """Handle a key-specific change record."""
        # Only fire if the value actually changed from the last reported value
        old_val = self._key_cache.get(record.key)
        if old_val is None or old_val != record.new_value:
            self._key_cache[record.key] = record.new_value
            # Increment render count and set version before calling on_change
            self._render_count += 1
            self._render_version = self._render_count
            self.on_change()

    def detach(self) -> None:
        """Unsubscribe from all state changes."""
        current_state = self.store.get()
        for key in self.keys:
            self._key_cache[key] = current_state.get(key)
        for unsub in self._unsubs:
            with contextlib.suppress(Exception):
                unsub()
        self._unsubs.clear()

    def update_keys(self, new_keys: list[str]) -> None:
        """Update the list of keys to watch. Re-subscribes without re-rendering."""
        self.detach()
        self.keys = new_keys
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        """Set up subscriptions without triggering on_change."""
        if self.keys:
            for key in self.keys:
                unsub = self.store.subscribe_to_key(
                    key,
                    lambda record, ver, key=key: self._handle_key_change(record, ver),
                )
                self._unsubs.append(unsub)
        else:
            def wrapped_listener() -> None:
                self.on_change()

            unsub = self.store.subscribe(wrapped_listener)
            self._unsubs.append(unsub)


class SelectorSubscription:
    """
    Subscription that uses a selector for efficient updates.

    Only notifies when the selected value changes, not on every state change.
    """

    def __init__(
        self,
        selector: Any,
        on_change: Callable[[], None],
    ) -> None:
        self._selector = selector
        self._on_change = on_change
        self._unsub: Callable[[], None] | None = None

    def attach(self) -> None:
        """Start listening for selector changes."""
        if self._unsub is not None:
            # Already attached; do nothing
            return
        sel = self._selector
        _initial = sel.get()  # prime the selector cache and get initial value
        # Force the selector to fire on_change once for the initial value
        sel._force_next = True
        self._unsub = sel.subscribe(self._on_change)

    def detach(self) -> None:
        """Stop listening."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def get_value(self) -> Any:
        """Get the current selected value."""
        return self._selector.get()


def create_widget_subscription(
    store: AppStateStore,
    keys: list[str],
    render: Callable[[], None],
) -> StateSubscription:
    """Factory function to create a StateSubscription for a Textual widget."""
    return StateSubscription(store=store, on_change=render, keys=keys)
