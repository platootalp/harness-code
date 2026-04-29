"""React-style hooks for state management."""
from __future__ import annotations

from typing import Callable, TypeVar

from .store import Store

T = TypeVar('T')

# Global store instance - set by repl_launcher
_store: Store | None = None
_set_state: Callable[[Callable], None] | None = None


def init_store(store: Store) -> None:
    global _store, _set_state
    _store = store
    _set_state = store.set_state


def use_app_state(selector: Callable[[T], T]) -> T:
    """Selector-based subscription. Re-renders when selected slice changes."""
    if _store is None:
        raise RuntimeError("Store not initialized")
    return selector(_store.get_state())


def use_set_app_state() -> Callable[[Callable], None]:
    """Returns the store's set_state directly."""
    if _set_state is None:
        raise RuntimeError("Store not initialized")
    return _set_state
