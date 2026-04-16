"""
Tests for AsyncObservable state store.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from claude_code.state.store import AsyncObservable


@pytest.fixture
def store() -> AsyncObservable[int]:
    """Create a store with initial state 0."""
    return AsyncObservable(0)


class TestAsyncObservableInit:
    """Tests for AsyncObservable initialization."""

    def test_initial_state(self) -> None:
        store = AsyncObservable(42)
        assert store.get_state_sync() == 42

    def test_initial_state_with_complex_type(self) -> None:
        store = AsyncObservable({"key": "value"})
        assert store.get_state_sync() == {"key": "value"}

    def test_no_listeners_initially(self) -> None:
        store = AsyncObservable(0)
        assert not store.has_listeners()
        assert store.listener_count() == 0


class TestSubscribe:
    """Tests for subscribe functionality."""

    def test_subscribe_adds_listener(self) -> None:
        store = AsyncObservable(0)

        async def callback(new: int, old: int) -> None:
            pass

        _ = asyncio.run(store.subscribe(callback))
        assert store.has_listeners()
        assert store.listener_count() == 1

    def test_subscribe_returns_unsubscribe(self) -> None:
        store = AsyncObservable(0)

        async def callback(new: int, old: int) -> None:
            pass

        unsub = asyncio.run(store.subscribe(callback))
        unsub()
        assert not store.has_listeners()

    def test_multiple_subscribers(self) -> None:
        store = AsyncObservable(0)
        results: list[tuple[int, int]] = []

        async def callback1(new: int, old: int) -> None:
            results.append((new, old))

        async def callback2(new: int, old: int) -> None:
            results.append((new, old))

        unsub1 = asyncio.run(store.subscribe(callback1))
        unsub2 = asyncio.run(store.subscribe(callback2))

        assert store.listener_count() == 2

        unsub1()
        assert store.listener_count() == 1
        assert store.has_listeners()

        unsub2()
        assert not store.has_listeners()


class TestSetState:
    """Tests for set_state functionality."""

    def test_set_state_updates_state(self) -> None:
        store = AsyncObservable(0)
        asyncio.run(store.set_state(5))
        assert store.get_state_sync() == 5

    def test_set_state_notifies_listeners(self) -> None:
        store = AsyncObservable(0)
        results: list[tuple[int, int]] = []

        async def callback(new: int, old: int) -> None:
            results.append((new, old))

        asyncio.run(store.subscribe(callback))
        asyncio.run(store.set_state(10))

        assert results == [(10, 0)]

    def test_set_state_multiple_updates(self) -> None:
        store = AsyncObservable(0)
        results: list[tuple[int, int]] = []

        async def callback(new: int, old: int) -> None:
            results.append((new, old))

        asyncio.run(store.subscribe(callback))
        asyncio.run(store.set_state(1))
        asyncio.run(store.set_state(2))
        asyncio.run(store.set_state(3))

        assert results == [(1, 0), (2, 1), (3, 2)]

    def test_set_state_same_reference_no_notify(self) -> None:
        """Setting state to the same object reference should not notify."""
        store = AsyncObservable({"key": "value"})
        results: list[tuple[Any, Any]] = []

        async def callback(new: Any, old: Any) -> None:
            results.append((new, old))

        asyncio.run(store.subscribe(callback))
        current = store.get_state_sync()
        asyncio.run(store.set_state(current))

        assert results == []

    def test_set_state_notifies_all_subscribers(self) -> None:
        store = AsyncObservable(0)
        results1: list[tuple[int, int]] = []
        results2: list[tuple[int, int]] = []

        async def callback1(new: int, old: int) -> None:
            results1.append((new, old))

        async def callback2(new: int, old: int) -> None:
            results2.append((new, old))

        asyncio.run(store.subscribe(callback1))
        asyncio.run(store.subscribe(callback2))
        asyncio.run(store.set_state(7))

        assert results1 == [(7, 0)]
        assert results2 == [(7, 0)]


class TestUnsubscribe:
    """Tests for unsubscribe functionality."""

    def test_unsubscribe_removes_callback(self) -> None:
        store = AsyncObservable(0)
        results: list[tuple[int, int]] = []

        async def callback(new: int, old: int) -> None:
            results.append((new, old))

        asyncio.run(store.subscribe(callback))
        store.unsubscribe(callback)
        asyncio.run(store.set_state(99))

        assert results == []


class TestConcurrency:
    """Tests for concurrent access and locking."""

    @pytest.mark.asyncio
    async def test_concurrent_set_state(self) -> None:
        """Multiple concurrent set_state calls should not corrupt state."""
        store = AsyncObservable(0)

        async def update(value: int) -> None:
            await store.set_state(value)

        await asyncio.gather(*[update(i) for i in range(1, 11)])
        # Final state is one of the values (last writer wins), but no corruption
        assert isinstance(store.get_state_sync(), int)

    @pytest.mark.asyncio
    async def test_get_state_during_set_state(self) -> None:
        """Reading state while setting should work correctly."""
        store = AsyncObservable(0)
        results: list[int] = []

        async def reader() -> None:
            for _ in range(100):
                results.append(await store.get_state())
                await asyncio.sleep(0)

        async def writer() -> None:
            for i in range(1, 51):
                await store.set_state(i)

        await asyncio.gather(reader(), writer())

    def test_subscribe_during_set_state(self) -> None:
        """Subscribing after set_state should add a new listener."""
        store = AsyncObservable(0)

        async def noop_callback1(new: int, old: int) -> None:
            pass

        async def noop_callback2(new: int, old: int) -> None:
            pass

        asyncio.run(store.subscribe(noop_callback1))
        asyncio.run(store.set_state(1))
        asyncio.run(store.subscribe(noop_callback2))

        assert store.listener_count() == 2


class TestGenericTyping:
    """Tests to verify generic typing works correctly."""

    def test_typed_store_int(self) -> None:
        store: AsyncObservable[int] = AsyncObservable(0)
        assert store.get_state_sync() == 0

    def test_typed_store_str(self) -> None:
        store: AsyncObservable[str] = AsyncObservable("hello")
        assert store.get_state_sync() == "hello"

    def test_typed_store_complex(self) -> None:
        store: AsyncObservable[dict[str, list[int]]] = AsyncObservable(
            {"a": [1, 2, 3]}
        )
        assert store.get_state_sync() == {"a": [1, 2, 3]}
