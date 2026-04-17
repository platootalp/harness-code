"""
StateChangeHandler - Centralized handler for state change side-effects.

Manages key-specific handlers and global handlers that fire on state transitions.
Used by AppStateStore to coordinate external system sync (settings persistence,
auth cache clearing, etc.).

Migrated from src/state/handlers.ts pattern.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Type aliases
KeyHandler = Callable[[Any, Any], Awaitable[None] | None]
GlobalHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[None] | None]


class StateChangeHandler:
    """
    Central handler for state change side-effects.

    Registers handlers for specific keys or any state change.
    Handlers are async-aware and run safely in the event loop.

    Example:
        handler = StateChangeHandler()

        # Handle specific key changes
        handler.on_key_change("settings", my_settings_handler)

        # Handle any state change
        handler.on_any_change(my_global_handler)

        # Called by AppStateStore when state changes
        await handler.handle_change(old_state, new_state)
    """

    def __init__(self) -> None:
        self._key_handlers: dict[str, list[KeyHandler]] = {}
        self._global_handlers: list[GlobalHandler] = []

    def on_key_change(
        self,
        key: str,
        handler: KeyHandler,
    ) -> Callable[[], None]:
        """
        Register a handler for a specific key change.

        Args:
            key: The state key to watch.
            handler: Called with (old_value, new_value) when the key changes.
                     Can be sync or async.

        Returns:
            Unsubscribe function to remove the handler.

        Example:
            unsub = handler.on_key_change("settings", my_handler)
            unsub()  # removes the handler
        """
        if key not in self._key_handlers:
            self._key_handlers[key] = []
        self._key_handlers[key].append(handler)

        def unsubscribe() -> None:
            if key in self._key_handlers:
                self._key_handlers[key].remove(handler)
                if not self._key_handlers[key]:
                    del self._key_handlers[key]

        return unsubscribe

    def on_any_change(self, handler: GlobalHandler) -> Callable[[], None]:
        """
        Register a handler for any state change.

        Args:
            handler: Called with (old_state, new_state) on any change.
                     Can be sync or async.

        Returns:
            Unsubscribe function to remove the handler.

        Example:
            unsub = handler.on_any_change(my_handler)
            unsub()
        """
        self._global_handlers.append(handler)

        def unsubscribe() -> None:
            self._global_handlers.remove(handler)

        return unsubscribe

    async def handle_change(
        self,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> None:
        """
        Process all registered handlers for a state change.

        Called by AppStateStore's on_change callback.
        Runs key-specific handlers first, then global handlers.
        Errors in handlers are caught and logged but do not propagate.

        Args:
            old_state: The state before the change.
            new_state: The state after the change.
        """
        # Key-specific handlers
        all_keys = set(old_state.keys()) | set(new_state.keys())
        for key in all_keys:
            if old_state.get(key) != new_state.get(key):
                for handler in self._key_handlers.get(key, []):
                    try:
                        result = handler(old_state.get(key), new_state.get(key))
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.warning(
                            f"StateChangeHandler: {key} handler error: {e}"
                        )

        # Global handlers
        for handler in self._global_handlers:
            try:
                result = handler(old_state, new_state)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"StateChangeHandler: global handler error: {e}")

    @property
    def registered_keys(self) -> list[str]:
        """Return list of keys that have registered handlers."""
        return list(self._key_handlers.keys())

    @property
    def global_handler_count(self) -> int:
        """Return the number of global handlers."""
        return len(self._global_handlers)
