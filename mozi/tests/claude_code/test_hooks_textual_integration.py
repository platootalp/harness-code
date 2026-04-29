"""
Tests for hooks/textual_integration.py - Textual component state subscriptions.
"""

from __future__ import annotations

import pytest

from src.claude_code.hooks.app_state_store import AppStateStore
from src.claude_code.hooks.selector import SelectorState
from src.claude_code.hooks.textual_integration import (
    SelectorSubscription,
    StateSubscription,
    create_widget_subscription,
)


class TestStateSubscription:
    """Tests for StateSubscription."""

    def test_attach_subscribes_and_renders(self) -> None:
        """attach() subscribes and calls on_change."""
        store = AppStateStore()
        render_calls: list[int] = []

        sub = StateSubscription(store, lambda: render_calls.append(sub._render_version))
        sub.attach()
        assert render_calls == [0]  # initial render

        sub.detach()

    def test_key_subscription(self) -> None:
        """Key-specific subscriptions only fire for those keys."""
        store = AppStateStore({"count": 0, "name": "a"})
        render_calls: list[int] = []

        sub = StateSubscription(
            store, lambda: render_calls.append(sub._render_version), keys=["count"]
        )
        sub.attach()

        store.set(lambda s: {**s, "name": "b"})  # count unchanged
        assert render_calls == [0]  # only initial

        store.set(lambda s: {**s, "count": 5})
        assert render_calls == [0, 1]  # new render for count change (local render count)

        sub.detach()

    def test_detach_unsubscribes(self) -> None:
        """detach() stops all subscriptions."""
        store = AppStateStore({"x": 0})
        calls: list = []

        sub = StateSubscription(store, lambda: calls.append(1), keys=["x"])
        sub.attach()
        sub.detach()

        store.set(lambda s: {**s, "x": 99})
        assert len(calls) == 1  # 1 call from attach; detach prevents further calls

    def test_update_keys_resubscribes(self) -> None:
        """update_keys() resubscribes to new key set."""
        store = AppStateStore({"a": 0, "b": 0})
        calls: list[int] = []

        sub = StateSubscription(store, lambda: calls.append(sub._render_version), keys=["a"])
        sub.attach()
        assert calls == [0]

        store.set(lambda s: {**s, "a": 1})
        assert calls == [0, 1]

        sub.update_keys(["b"])
        # update_keys does NOT call on_change (initial state already rendered)
        store.set(lambda s: {**s, "b": 1})
        assert calls == [0, 1, 2]  # new version after b change


class TestSelectorSubscription:
    """Tests for SelectorSubscription."""

    def test_attach_and_get_value(self) -> None:
        """SelectorSubscription attaches and returns value without firing on initial attach."""
        store = AppStateStore({"items": [1, 2, 3]})
        selector = SelectorState(store, lambda s: len(s.get("items", [])))
        calls: list[int] = []

        sub = SelectorSubscription(selector, lambda: calls.append(selector.get()))
        sub.attach()
        # get_value returns the initial value without firing on_change on attach
        assert sub.get_value() == 3
        assert calls == []  # no fire on initial attach; fires only on selected value change

        sub.detach()

    def test_only_fires_on_selected_change(self) -> None:
        """SelectorSubscription only fires when selected value changes, not on attach."""
        store = AppStateStore({"items": [1, 2, 3], "other": "foo"})
        selector = SelectorState(store, lambda s: len(s.get("items", [])))
        calls: list = []

        sub = SelectorSubscription(selector, lambda: calls.append(1))
        sub.attach()
        # No fire on initial attach (selector value hasn't "changed" yet)
        assert len(calls) == 0

        store.set(lambda s: {**s, "other": "bar"})  # items unchanged, selector fires no
        assert len(calls) == 0

        store.set(lambda s: {**s, "items": [1]})  # items changed, selector fires
        assert len(calls) == 1

        sub.detach()


class TestCreateWidgetSubscription:
    """Tests for create_widget_subscription factory."""

    def test_creates_and_attachs_subscription(self) -> None:
        """Factory creates a ready-to-use subscription."""
        store = AppStateStore()
        calls: list = []

        sub = create_widget_subscription(store, ["x"], lambda: calls.append(1))
        sub.attach()
        assert calls == [1]

        sub.detach()
