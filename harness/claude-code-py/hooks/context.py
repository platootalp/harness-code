"""
Context - Global state access via ContextVar.

Provides thread/async-safe access to the application state store using Python's
contextvars module. This replaces React's Context for the Python/Textual architecture.

Usage:
    from .context import app_state_context, get_app_state

    # In app initialization:
    app_state_context.set(my_store)

    # In components/handlers:
    store = get_app_state()
    state = store.get()
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .app_state_store import AppStateStore

# Context variable for the app-wide state store.
# Set via app_state_context.set(store) in app initialization.
# Multiple concurrent contexts (e.g., in async tasks) get isolated values.
app_state_context: ContextVar[AppStateStore | None] = ContextVar(
    "app_state_context", default=None
)


def get_app_state() -> AppStateStore:
    """
    Get the current AppStateStore from context.

    Raises:
        RuntimeError: If the context is not set (forgot to call app_state_context.set).

    Example:
        store = get_app_state()
        state = store.get()
        print(f"Settings: {state.get('settings')}")
    """
    store = app_state_context.get()
    if store is None:
        raise RuntimeError(
            "AppStateStore not set in context. "
            "Call app_state_context.set(store) in app initialization."
        )
    return store


def set_app_state(store: AppStateStore) -> None:
    """
    Set the AppStateStore in the current context.

    Args:
        store: The AppStateStore instance to make globally accessible.

    Example:
        set_app_state(AppStateStore())
    """
    app_state_context.set(store)


def clear_app_state() -> None:
    """Clear the AppStateStore from context."""
    app_state_context.set(None)


def has_app_state() -> bool:
    """Return True if AppStateStore is set in context."""
    return app_state_context.get() is not None
