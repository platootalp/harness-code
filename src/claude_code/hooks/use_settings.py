"""
use_settings - Read-only access to settings from app state.

Provides a convenience class and function for accessing settings
from the global app state store, matching the TypeScript useSettings() pattern.

Migrated from src/hooks/useSettings.ts pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from .app_state_store import AppStateStore
    from .observable import AsyncObservable


class SettingsSlice:
    """
    Read-only view of settings in app state.

    Provides convenience methods for accessing settings keys
    without directly indexing the state dictionary.

    Example:
        settings = SettingsSlice(app_store)
        theme = settings.get_key("theme", "default")
        model = settings.get_key("model")
        all_settings = settings.get()
    """

    def __init__(self, store: AsyncObservable[dict[str, Any]] | AppStateStore) -> None:
        self._store = store

    def get(self) -> dict[str, Any]:
        """Get the full settings dictionary."""
        state = self._store.get()
        return cast("dict[str, Any]", state.get("settings", {}))

    def get_key(self, key: str, default: Any = None) -> Any:
        """
        Get a specific settings key with optional default.

        Args:
            key: The settings key to retrieve.
            default: Value to return if key is not found.

        Returns:
            The settings value or default.
        """
        return self.get().get(key, default)

    def has_key(self, key: str) -> bool:
        """Return True if the settings key exists."""
        return key in self.get()

    def __repr__(self) -> str:
        return f"SettingsSlice({len(self.get())} keys)"


def use_settings(
    store: AsyncObservable[dict[str, Any]] | AppStateStore | None = None,
) -> SettingsSlice:
    """
    Get a read-only settings slice from app state.

    If no store is provided, retrieves the global store from context.

    Args:
        store: Optional explicit store. If None, uses get_app_state().

    Returns:
        A SettingsSlice for read-only settings access.

    Example:
        # With explicit store
        settings = use_settings(my_store)
        theme = settings.get_key("theme")

        # With global context
        settings = use_settings()
        model = settings.get_key("model")
    """
    if store is None:
        from .context import get_app_state

        store = get_app_state()
    return SettingsSlice(store)
