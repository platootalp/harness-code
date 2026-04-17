"""
SelectorState - Derived state with subscription and memoization.

Provides a selector pattern where a derived value is computed from state
and only updates when the selected value actually changes (not on every state change).

Migrated from src/hooks/useSelector.ts pattern.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from .observable import AsyncObservable

T = TypeVar("T")
U = TypeVar("U")


class SelectorState(Generic[T, U]):
    """
    Caches selector output, only notifies when selected value changes.

    A selector derives a value from the full state. It only fires subscribers
    when the derived value changes (structural equality check).

    Example:
        store = AsyncObservable({"count": 0, "name": "test"})

        # Create a selector for the count
        count_selector = SelectorState(
            store,
            selector=lambda state: state.get("count", 0)
        )

        # Subscribe to count changes only
        unsub = count_selector.subscribe(lambda: print(f"count changed!"))
        print(count_selector.get())  # 0

        store.set(lambda s: {**s, "count": 1})  # Notifies subscriber
        print(count_selector.get())  # 1

        store.set(lambda s: {**s, "name": "new"})  # Does NOT notify (count unchanged)
    """

    def __init__(
        self,
        store: AsyncObservable[T],
        selector: Callable[[T], U],
    ) -> None:
        self._store = store
        self._selector = selector
        self._cached_value: U | None = None
        self._cache_version = -1
        self._unsub_store: Callable[[], None] | None = None
        self._force_next = False

    def get(self) -> U:
        """
        Get current selected value, recomputing if needed.

        Returns the cached value if the selector output hasn't changed.
        Initializes the cache on first call.
        """
        current_version = self._store.version

        if self._cache_version == current_version:
            return self._cached_value  # type: ignore

        state = self._store.get()
        self._cached_value = self._selector(state)
        self._cache_version = current_version

        return self._cached_value

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        """
        Subscribe to changes in the selected value.

        The listener fires only when the selector output changes,
        not on every state change.

        Args:
            listener: Callback with no arguments fired when selected value changes.

        Returns:
            Unsubscribe function.
        """
        # Initialize cache with current value before subscribing
        self.get()

        def notify_if_changed(_version: int | None = None) -> None:
            """Called by store with optional version. We use the selector pattern."""
            old = self._cached_value
            new = self._selector(self._store.get())
            if new != old or self._force_next:
                self._force_next = False
                self._cached_value = new
                self._cache_version = self._store.version
                listener()
            elif old is not None:
                self._cache_version = self._store.version

        self._force_next = False
        if self._unsub_store is None:
            self._unsub_store = self._store.subscribe(notify_if_changed)

        # Store listener for tracking
        if not hasattr(self, "_listeners"):
            self._listeners: list[Callable[[], None]] = []
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if hasattr(self, "_listeners"):
                self._listeners.remove(listener)
            if self._unsub_store is not None:
                self._unsub_store()
                self._unsub_store = None

        return unsubscribe

    def invalidate(self) -> None:
        """Force invalidation of the cached value on next get()."""
        self._cache_version = -1

    @property
    def version(self) -> int:
        """Return the store's version for cache invalidation."""
        return self._store.version
