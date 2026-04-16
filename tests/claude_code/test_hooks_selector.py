"""
Tests for hooks/selector.py - SelectorState.
"""

from __future__ import annotations

import asyncio

import pytest

from src.claude_code.hooks.app_state_store import AppStateStore
from src.claude_code.hooks.selector import SelectorState


class TestSelectorState:
    """Tests for SelectorState."""

    def test_get_returns_selected_value(self) -> None:
        """get() returns the selector's output."""
        store = AppStateStore({"count": 5, "name": "test"})
        selector = SelectorState(store, lambda s: s.get("count", 0))
        assert selector.get() == 5

    def test_get_memoizes(self) -> None:
        """get() doesn't recompute if value unchanged."""
        store = AppStateStore({"items": [1, 2, 3]})
        compute_count: list[int] = []

        def selector(state: dict) -> int:
            compute_count.append(1)
            return len(state.get("items", []))

        selector_state = SelectorState(store, selector)
        selector_state.get()  # computes
        selector_state.get()  # cached
        assert len(compute_count) == 1

    def test_subscribe_fires_on_change(self) -> None:
        """subscribe() fires when selected value changes."""
        store = AppStateStore({"count": 0})
        selector = SelectorState(store, lambda s: s.get("count", 0))
        calls: list[int] = []

        unsub = selector.subscribe(lambda: calls.append(selector.get()))

        store.set(lambda s: {**s, "count": 10})
        assert calls == [10]

        unsub()

    def test_subscribe_ignores_non_selected_changes(self) -> None:
        """subscribe() ignores changes to unselected keys."""
        store = AppStateStore({"count": 0, "other": "foo"})
        selector = SelectorState(store, lambda s: s.get("count", 0))
        calls: list = []

        unsub = selector.subscribe(lambda: calls.append(1))

        store.set(lambda s: {**s, "other": "bar"})
        assert len(calls) == 0

        unsub()

    def test_subscribe_returns_unsubscribe(self) -> None:
        """subscribe() returns a working unsubscribe function."""
        store = AppStateStore({"count": 0})
        selector = SelectorState(store, lambda s: s.get("count", 0))
        calls: list[int] = []

        unsub = selector.subscribe(lambda: calls.append(selector.get()))
        unsub()

        store.set(lambda s: {**s, "count": 99})
        assert len(calls) == 0

    def test_invalidate_clears_cache(self) -> None:
        """invalidate() forces recomputation on next get()."""
        store = AppStateStore({"x": 1})
        compute_count: list[int] = []

        selector = SelectorState(store, lambda s: (compute_count.append(1), s.get("x"))[1])
        selector.get()
        assert len(compute_count) == 1

        selector.invalidate()
        selector.get()
        assert len(compute_count) == 2

    def test_version_property(self) -> None:
        """version property returns store's version."""
        store = AppStateStore()
        selector = SelectorState(store, lambda s: s.get("x"))
        assert selector.version == 0
        store.set(lambda s: {**s, "x": 1})
        assert selector.version == 1
