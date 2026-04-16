"""
State change hooks for the Claude Code state system.

Provides an `on_change` decorator for registering callbacks that fire when
state changes occur in an AsyncObservable store.

Migrated from src/state/AppStateStore.ts (TypeScript).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar

from .store import AsyncObservable

T = TypeVar("T")

StateChangeCallback = Callable[[T, T], Awaitable[None]]
ChangeHook = Callable[[T, T], Awaitable[None]]


def on_change(
    store: AsyncObservable[T],
) -> Callable[[Callable[[T, T], Awaitable[None]]], Callable[[T, T], Awaitable[None]]]:
    """
    Decorator that registers a callback to be called whenever the store's state changes.

    This is a thin wrapper around AsyncObservable.subscribe that provides a
    decorator interface for convenience.

    Args:
        store: The AsyncObservable instance to subscribe to.

    Returns:
        A decorator that registers the decorated function as a state change listener.

    Example:
        store = AsyncObservable({"count": 0})

        @on_change(store)
        async def log_change(new_state, old_state):
            print(f"Changed from {old_state} to {new_state}")

        await store.set_state({"count": 1})  # prints: Changed from {'count': 0} to {'count': 1}
    """

    def decorator(
        callback: Callable[[T, T], Awaitable[None]],
    ) -> Callable[[T, T], Awaitable[None]]:
        store.subscribe_sync(callback)
        return callback

    return decorator


def on_change_sync(
    store: AsyncObservable[T],
) -> Callable[
    [Callable[[T, T], None]], Callable[[T, T], None]
]:
    """
    Decorator that registers a synchronous callback to be called whenever
    the store's state changes.

    Unlike `on_change` which expects an async callback, this decorator wraps
    the synchronous function so it integrates with the async subscription
    system.

    Args:
        store: The AsyncObservable instance to subscribe to.

    Returns:
        A decorator that registers the decorated sync function as a listener.

    Example:
        store = AsyncObservable({"count": 0})

        @on_change_sync(store)
        def log_change(new_state, old_state):
            print(f"Changed from {old_state} to {new_state}")
    """

    def make_wrapper(
        callback: Callable[[T, T], None],
    ) -> Callable[[T, T], Awaitable[None]]:
        async def async_wrapper(new_state: T, old_state: T) -> None:
            callback(new_state, old_state)

        return async_wrapper

    def decorator(
        callback: Callable[[T, T], None],
    ) -> Callable[[T, T], None]:
        store.subscribe_sync(make_wrapper(callback))
        return callback

    return decorator


# Type variable for ChangeHookManager (class-scoped)
S = TypeVar("S")


class ChangeHookManager(Generic[S]):
    """
    Manager for multiple named hooks on a store.

    Provides a registry of named change callbacks that can be added,
    removed, and listed dynamically.

    Example:
        manager = ChangeHookManager(store)

        async def on_tasks_update(new_state, old_state):
            print("Tasks updated")

        manager.register("tasks", on_tasks_update)
        manager.unregister("tasks")
    """

    def __init__(self, store: AsyncObservable[S]) -> None:
        self._store = store
        self._hooks: dict[str, ChangeHook[S]] = {}
        self._unsubscribes: dict[str, Callable[[], None]] = {}

    def register(self, name: str, callback: ChangeHook[S]) -> None:
        """
        Register a named change hook.

        Args:
            name: Unique identifier for this hook.
            callback: Async function called with (new_state, old_state).

        Raises:
            ValueError: If a hook with this name is already registered.
        """
        if name in self._hooks:
            raise ValueError(f"Hook '{name}' is already registered")
        self._hooks[name] = callback
        self._unsubscribes[name] = self._store.subscribe_sync(callback)

    def unregister(self, name: str) -> None:
        """
        Unregister a named change hook.

        Args:
            name: Identifier of the hook to remove.

        Raises:
            KeyError: If no hook with this name is registered.
        """
        if name not in self._hooks:
            raise KeyError(f"Hook '{name}' is not registered")
        self._unsubscribes[name]()
        del self._hooks[name]
        del self._unsubscribes[name]

    def is_registered(self, name: str) -> bool:
        """Return True if a hook with the given name is registered."""
        return name in self._hooks

    def list_hooks(self) -> list[str]:
        """Return a list of all registered hook names."""
        return list(self._hooks.keys())

