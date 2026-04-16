"""Minimal pub/sub Store implementation."""
from __future__ import annotations

from typing import Callable, Generic, TypeVar

T = TypeVar('T')


class Store(Generic[T]):
    """Minimal imperative pub/sub store - no framework dependency."""

    def __init__(self, initial: T) -> None:
        self._state: T = initial
        self._listeners: list[Callable[[], None]] = []

    def get_state(self) -> T:
        return self._state

    def set_state(self, updater: Callable[[T], T]) -> None:
        self._state = updater(self._state)
        for listener in self._listeners:
            listener()

    def subscribe(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)


def create_store(initial: T) -> Store[T]:
    return Store(initial)
