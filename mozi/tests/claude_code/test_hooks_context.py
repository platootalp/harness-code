"""
Tests for hooks/context.py - ContextVar for app-wide state access.
"""

from __future__ import annotations

import pytest

from src.claude_code.hooks.app_state_store import AppStateStore
from src.claude_code.hooks.context import (
    app_state_context,
    clear_app_state,
    get_app_state,
    has_app_state,
    set_app_state,
)


class TestAppStateContext:
    """Tests for the app state context variable."""

    def test_get_app_state_raises_when_not_set(self) -> None:
        """get_app_state() raises RuntimeError when context is not set."""
        clear_app_state()
        with pytest.raises(RuntimeError, match="not set in context"):
            get_app_state()

    def test_set_and_get(self) -> None:
        """set_app_state() and get_app_state() work together."""
        clear_app_state()
        store = AppStateStore()
        set_app_state(store)
        assert get_app_state() is store
        clear_app_state()

    def test_has_app_state_false_when_empty(self) -> None:
        """has_app_state() returns False when context is empty."""
        clear_app_state()
        assert has_app_state() is False

    def test_has_app_state_true_when_set(self) -> None:
        """has_app_state() returns True when context is set."""
        clear_app_state()
        store = AppStateStore()
        set_app_state(store)
        assert has_app_state() is True
        clear_app_state()

    def test_clear_app_state(self) -> None:
        """clear_app_state() removes the store from context."""
        clear_app_state()
        store = AppStateStore()
        set_app_state(store)
        clear_app_state()
        assert has_app_state() is False

    def test_isolation_between_contexts(self) -> None:
        """Stores are isolated between different async contexts."""
        import asyncio

        clear_app_state()
        store_a = AppStateStore({"name": "a"})
        store_b = AppStateStore({"name": "b"})

        results: dict[str, str] = {}

        async def check_a() -> None:
            set_app_state(store_a)
            results["a"] = get_app_state().get()["name"]

        async def check_b() -> None:
            set_app_state(store_b)
            results["b"] = get_app_state().get()["name"]

        async def check_main() -> None:
            results["main"] = "none" if not has_app_state() else get_app_state().get()["name"]

        async def run() -> None:
            await asyncio.gather(
                check_a(),
                check_b(),
                check_main(),
            )

        asyncio.run(run())

        assert results["a"] == "a"
        assert results["b"] == "b"
        clear_app_state()
