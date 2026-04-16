"""
AsyncObservable generic state store with subscribe/set_state/lock mechanism.

Migrated from src/state/store.ts (TypeScript).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

T = TypeVar("T")

StateChangeCallback = Callable[[T, T], Awaitable[None]]


class AsyncObservable(Generic[T]):
    """
    A generic observable state store with async subscription and locking.

    Provides thread/async-safe state mutations with subscriber notification.
    Mirrors the TypeScript Store<T> interface but with async support.
    """

    def __init__(self, initial_state: T) -> None:
        self._state: T = initial_state
        self._listeners: set[StateChangeCallback[T]] = set()
        self._lock = asyncio.Lock()

    async def get_state(self) -> T:
        """Return the current state (async-safe)."""
        async with self._lock:
            return self._state

    def get_state_sync(self) -> T:
        """Return the current state synchronously (for non-async contexts)."""
        return self._state

    async def set_state(self, new_state: T) -> None:
        """
        Update state and notify all subscribers.

        Uses a lock to prevent concurrent modifications.
        Only notifies if the new state is different from the current state.
        """
        async with self._lock:
            prev = self._state
            if prev is new_state:
                return
            self._state = new_state

        # Notify subscribers outside the lock to avoid deadlocks
        for listener in list(self._listeners):
            await listener(new_state, prev)

    async def subscribe(self, callback: StateChangeCallback[T]) -> Callable[[], None]:
        """
        Subscribe to state changes.

        Args:
            callback: Async function called with (new_state, old_state) on each change.

        Returns:
            Unsubscribe function to remove the subscription.
        """
        self._listeners.add(callback)

        def unsubscribe() -> None:
            self._listeners.discard(callback)

        return unsubscribe

    def subscribe_sync(self, callback: StateChangeCallback[T]) -> Callable[[], None]:
        """
        Synchronously subscribe to state changes (non-blocking).

        Unlike subscribe(), this method does not acquire the lock and is
        suitable for use in synchronous contexts (e.g., decorators).
        The callback will still be called asynchronously when state changes.

        Args:
            callback: Async function called with (new_state, old_state) on each change.

        Returns:
            Unsubscribe function to remove the subscription.
        """
        self._listeners.add(callback)

        def unsubscribe() -> None:
            self._listeners.discard(callback)

        return unsubscribe

    def unsubscribe(self, callback: StateChangeCallback[T]) -> None:
        """
        Remove a subscriber from the store.

        Args:
            callback: The callback that was passed to subscribe().
        """
        self._listeners.discard(callback)

    def has_listeners(self) -> bool:
        """Return True if there are any active subscribers."""
        return len(self._listeners) > 0

    def listener_count(self) -> int:
        """Return the number of active subscribers."""
        return len(self._listeners)
