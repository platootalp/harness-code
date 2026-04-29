"""
Tests for hooks/app_state_store.py - AppStateStore.
"""

from __future__ import annotations

import asyncio

import pytest

from src.claude_code.hooks.app_state_store import AppStateStore


class TestAppStateStoreInit:
    """Tests for AppStateStore initialization."""

    def test_default_state(self) -> None:
        """Store initializes with default state."""
        store = AppStateStore()
        state = store.get()
        assert isinstance(state, dict)
        assert "settings" in state
        assert state["settings"] == {}
        assert state["verbose"] is False
        assert state["expandedView"] == "none"

    def test_custom_initial_state(self) -> None:
        """Store accepts custom initial state."""
        store = AppStateStore({"count": 42, "name": "test"})
        state = store.get()
        assert state["count"] == 42
        assert state["name"] == "test"

    def test_version_starts_at_zero(self) -> None:
        """Store version starts at 0."""
        store = AppStateStore()
        assert store.version == 0


class TestSet:
    """Tests for synchronous set()."""

    def test_set_updates_state(self) -> None:
        """set() updates the state."""
        store = AppStateStore()
        store.set(lambda s: {**s, "count": 5})
        assert store.get()["count"] == 5

    def test_set_identity_check(self) -> None:
        """set() does nothing if updater returns same reference."""
        store = AppStateStore()
        state = store.get()
        store.set(lambda s: s)  # returns same object
        assert store.version == 0  # no change

    def test_set_increments_version(self) -> None:
        """set() increments version."""
        store = AppStateStore()
        assert store.version == 0
        store.set(lambda s: {**s, "x": 1})
        assert store.version == 1
        store.set(lambda s: {**s, "x": 2})
        assert store.version == 2

    def test_set_triggers_subscribers(self) -> None:
        """set() triggers all subscribers."""
        store = AppStateStore()
        calls: list[int] = []

        unsub = store.subscribe(lambda: calls.append(store.version))
        store.set(lambda s: {**s, "x": 1})
        assert calls == [1]
        unsub()

    def test_set_multiple_subscribers(self) -> None:
        """Multiple subscribers all receive notifications."""
        store = AppStateStore()
        calls_a: list[int] = []
        calls_b: list[int] = []

        unsub_a = store.subscribe(lambda: calls_a.append(store.version))
        unsub_b = store.subscribe(lambda: calls_b.append(store.version))

        store.set(lambda s: {**s, "x": 1})
        assert calls_a == [1]
        assert calls_b == [1]

        unsub_a()
        unsub_b()


class TestSetAsync:
    """Tests for async set_async()."""

    @pytest.mark.asyncio
    async def test_set_async_updates_state(self) -> None:
        """set_async() updates the state."""
        store = AppStateStore()
        await store.set_async(lambda s: {**s, "loading": True})
        assert store.get()["loading"] is True

    @pytest.mark.asyncio
    async def test_set_async_awaits_effects(self) -> None:
        """set_async() runs on_change effects before notifying."""
        store = AppStateStore()
        effects: list[str] = []

        store.handler.on_key_change("count", lambda old, new: effects.append(new))

        await store.set_async(lambda s: {**s, "count": 10})
        assert effects == [10]

    @pytest.mark.asyncio
    async def test_set_async_increments_version(self) -> None:
        """set_async() increments version."""
        store = AppStateStore()
        await store.set_async(lambda s: {**s, "x": 1})
        assert store.version == 1


class TestSubscribeToKey:
    """Tests for subscribe_to_key()."""

    def test_key_subscription_fires(self) -> None:
        """subscribe_to_key() fires when the key changes."""
        store = AppStateStore()
        records: list = []

        unsub = store.subscribe_to_key("count", lambda r: records.append(r))
        store.set(lambda s: {**s, "count": 5})
        assert len(records) == 1
        assert records[0].key == "count"
        assert records[0].new_value == 5
        unsub()

    def test_key_subscription_ignores_other_keys(self) -> None:
        """subscribe_to_key() ignores changes to other keys."""
        store = AppStateStore()
        calls: list = []

        unsub = store.subscribe_to_key("count", lambda r: calls.append(r))
        store.set(lambda s: {**s, "name": "changed"})  # count unchanged
        assert len(calls) == 0
        unsub()

    def test_key_subscription_old_value_recorded(self) -> None:
        """ChangeRecord includes old_value."""
        store = AppStateStore({"count": 0})
        record_arg: list = []

        unsub = store.subscribe_to_key("count", lambda r: record_arg.append(r))
        store.set(lambda s: {**s, "count": 10})
        assert len(record_arg) == 1
        assert record_arg[0].old_value == 0
        assert record_arg[0].new_value == 10
        unsub()


class TestHandler:
    """Tests for StateChangeHandler integration."""

    def test_handler_on_key_change(self) -> None:
        """Handler's on_key_change fires correctly."""
        store = AppStateStore()
        calls: list[tuple] = []

        store.handler.on_key_change("settings", lambda old, new: calls.append((old, new)))

        store.set(lambda s: {**s, "settings": {"theme": "dark"}})
        assert len(calls) == 1
        assert calls[0] == ({}, {"theme": "dark"})

    def test_handler_on_any_change(self) -> None:
        """Handler's on_any_change fires on any state change."""
        store = AppStateStore()
        calls: list = []

        store.handler.on_any_change(lambda old, new: calls.append((old, new)))

        store.set(lambda s: {**s, "anything": "changed"})
        assert len(calls) == 1
        unsub = store.handler.on_any_change(lambda *_: None)
        unsub()

    def test_handler_unsubscribe(self) -> None:
        """Handler unsubscribe works."""
        store = AppStateStore()
        calls: list = []

        unsub = store.handler.on_key_change("x", lambda *_: calls.append(1))
        unsub()

        store.set(lambda s: {**s, "x": 1})
        assert len(calls) == 0

    def test_handler_registered_keys(self) -> None:
        """Handler tracks registered keys."""
        store = AppStateStore()
        assert "settings" in store.handler.registered_keys
        assert "permission_mode" in store.handler.registered_keys
