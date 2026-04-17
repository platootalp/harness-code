"""
Tests for state/hooks.py - state change hooks.
"""

from __future__ import annotations

import asyncio

import pytest

from src.claude_code.state.hooks import (
    ChangeHookManager,
    on_change,
    on_change_sync,
)
from src.claude_code.state.store import AsyncObservable


class TestOnChangeDecorator:
    """Tests for the on_change decorator."""

    @pytest.mark.asyncio
    async def test_on_change_decorator_called_on_state_change(self) -> None:
        """Decorator callback should fire when state changes."""
        store = AsyncObservable({"count": 0})
        calls: list[tuple[dict[str, int], dict[str, int]]] = []

        @on_change(store)
        async def on_change_callback(new_state, old_state):
            calls.append((new_state, old_state))

        await store.set_state({"count": 1})
        assert len(calls) == 1
        assert calls[0] == ({"count": 1}, {"count": 0})

    @pytest.mark.asyncio
    async def test_on_change_decorator_not_called_when_state_unchanged(
        self,
    ) -> None:
        """Decorator callback should not fire when state is unchanged."""
        store = AsyncObservable({"count": 0})
        calls: list[tuple[dict[str, int], dict[str, int]]] = []

        @on_change(store)
        async def on_change_callback(new_state, old_state):
            calls.append((new_state, old_state))

        # Set same state object (identity check)
        original = store.get_state_sync()
        await store.set_state(original)
        assert len(calls) == 0

    @pytest.mark.asyncio
    async def test_on_change_multiple_decorators(self) -> None:
        """Multiple decorators on same store should all be called."""
        store = AsyncObservable({"value": 0})
        calls_a: list[tuple[dict[str, int], dict[str, int]]] = []
        calls_b: list[tuple[dict[str, int], dict[str, int]]] = []

        @on_change(store)
        async def callback_a(new_state, old_state):
            calls_a.append((new_state, old_state))

        @on_change(store)
        async def callback_b(new_state, old_state):
            calls_b.append((new_state, old_state))

        await store.set_state({"value": 1})
        assert len(calls_a) == 1
        assert len(calls_b) == 1
        assert calls_a[0][0] == {"value": 1}
        assert calls_b[0][0] == {"value": 1}

    @pytest.mark.asyncio
    async def test_decorator_returns_function(self) -> None:
        """Decorator should return the original function."""
        store = AsyncObservable({"count": 0})

        def my_callback(new_state, old_state):
            pass

        decorated = on_change(store)(my_callback)
        assert decorated is my_callback


class TestOnChangeSyncDecorator:
    """Tests for the on_change_sync decorator."""

    @pytest.mark.asyncio
    async def test_sync_decorator_called_on_state_change(self) -> None:
        """Sync decorator callback should fire when state changes."""
        store = AsyncObservable({"count": 0})
        calls: list[tuple[dict[str, int], dict[str, int]]] = []

        @on_change_sync(store)
        def sync_callback(new_state, old_state):
            calls.append((new_state, old_state))

        await store.set_state({"count": 1})
        assert len(calls) == 1
        assert calls[0] == ({"count": 1}, {"count": 0})

    @pytest.mark.asyncio
    async def test_sync_decorator_returns_function(self) -> None:
        """Sync decorator should return the original sync function."""
        store = AsyncObservable({"count": 0})

        def sync_callback(new_state, old_state):
            pass

        decorated = on_change_sync(store)(sync_callback)
        assert decorated is sync_callback


class TestChangeHookManager:
    """Tests for the ChangeHookManager class."""

    @pytest.mark.asyncio
    async def test_register_and_unregister(self) -> None:
        """Hooks can be registered and unregistered by name."""
        store = AsyncObservable({"value": 0})
        manager = ChangeHookManager(store)
        calls: list[tuple[dict[str, int], dict[str, int]]] = []

        async def hook(new_state, old_state):
            calls.append((new_state, old_state))

        manager.register("my_hook", hook)
        assert manager.is_registered("my_hook")
        assert manager.list_hooks() == ["my_hook"]

        await store.set_state({"value": 1})
        assert len(calls) == 1

        manager.unregister("my_hook")
        assert not manager.is_registered("my_hook")
        assert manager.list_hooks() == []

        # After unregister, should not receive more calls
        await store.set_state({"value": 2})
        assert len(calls) == 1  # No new call

    @pytest.mark.asyncio
    async def test_register_duplicate_name_raises(self) -> None:
        """Registering a hook with an existing name raises ValueError."""
        store = AsyncObservable({"value": 0})
        manager = ChangeHookManager(store)

        async def hook(new_state, old_state):
            pass

        manager.register("hook1", hook)
        with pytest.raises(ValueError, match="already registered"):
            manager.register("hook1", hook)

    @pytest.mark.asyncio
    async def test_unregister_unknown_name_raises(self) -> None:
        """Unregistering an unknown hook raises KeyError."""
        store = AsyncObservable({"value": 0})
        manager = ChangeHookManager(store)

        with pytest.raises(KeyError, match="not registered"):
            manager.unregister("unknown")

    @pytest.mark.asyncio
    async def test_multiple_named_hooks(self) -> None:
        """Multiple named hooks can coexist independently."""
        store = AsyncObservable({"count": 0})
        manager = ChangeHookManager(store)
        calls_a: list = []
        calls_b: list = []

        async def hook_a(new_state, old_state):
            calls_a.append((new_state, old_state))

        async def hook_b(new_state, old_state):
            calls_b.append((new_state, old_state))

        manager.register("hook_a", hook_a)
        manager.register("hook_b", hook_b)

        await store.set_state({"count": 1})
        assert len(calls_a) == 1
        assert len(calls_b) == 1

        manager.unregister("hook_a")
        await store.set_state({"count": 2})
        assert len(calls_a) == 1  # No new call
        assert len(calls_b) == 2  # Still receiving
