"""
Tests for hooks/effect.py - @effect decorator.
"""

from __future__ import annotations

import pytest

from src.claude_code.hooks.app_state_store import AppStateStore
from src.claude_code.hooks.effect import effect, effect_state


class TestEffectDecorator:
    """Tests for the @effect decorator."""

    @pytest.mark.asyncio
    async def test_effect_runs_on_trigger(self) -> None:
        """Effect can be triggered manually via func.trigger()."""
        store = AppStateStore()
        calls: list[int] = []

        @effect(store=store)
        async def my_effect() -> None:
            calls.append(1)

        await my_effect.trigger()
        assert calls == [1]

    @pytest.mark.asyncio
    async def test_effect_runs_on_dep_mount(self) -> None:
        """Effect with on_mount=True runs immediately."""
        store = AppStateStore()
        calls: list[int] = []

        @effect(deps=[], on_mount=True, store=store)
        async def mount_effect() -> None:
            calls.append(1)

        # on_mount effects run on trigger(), not on decorator evaluation
        await mount_effect.trigger()
        assert calls == [1]

    @pytest.mark.asyncio
    async def test_effect_with_key_dep_triggers_on_change(self) -> None:
        """Effect with deps re-runs when dependency changes."""
        store = AppStateStore({"count": 0})
        prev_count: list[int] = []

        @effect(deps=["count"], store=store)
        async def count_effect() -> None:
            count = store.get()["count"]
            prev_count.append(count)

        # Trigger to initialize
        await count_effect.trigger()
        assert prev_count == [0]

        # Change the dependency
        store.set(lambda s: {**s, "count": 5})
        await count_effect.trigger()
        assert prev_count == [0, 5]

    @pytest.mark.asyncio
    async def test_effect_does_not_rerun_when_dep_unchanged(self) -> None:
        """Effect does not re-run when deps are unchanged."""
        store = AppStateStore({"a": 1, "b": 2})
        calls: list[int] = []

        @effect(deps=["a"], store=store)
        async def a_effect() -> None:
            calls.append(1)

        await a_effect.trigger()
        assert calls == [1]

        # Change b, not a
        store.set(lambda s: {**s, "b": 99})
        await a_effect.trigger()
        assert calls == [1]  # No new call

    @pytest.mark.asyncio
    async def test_effect_cleanup(self) -> None:
        """Effect cleanup runs registered cleanup functions."""
        store = AppStateStore()
        cleanup_calls: list[int] = []

        @effect(store=store)
        async def my_effect() -> None:
            pass

        my_effect._effect_cleanup.register(lambda: cleanup_calls.append(1))
        my_effect._effect_cleanup.cleanup()
        assert cleanup_calls == [1]

    @pytest.mark.asyncio
    async def test_effect_error_handling(self) -> None:
        """Effect errors are caught and don't propagate."""
        store = AppStateStore()
        errored: list[int] = []

        @effect(store=store)
        async def bad_effect() -> None:
            raise ValueError("test error")

        @effect(store=store)
        async def good_effect() -> None:
            errored.append(1)

        await bad_effect.trigger()
        await good_effect.trigger()
        # good_effect should still run
        assert errored == [1]


class TestEffectState:
    """Tests for effect_state() cleanup tracker."""

    def test_effect_state_register_and_cleanup(self) -> None:
        """EffectCleanup tracks and runs registered cleanups."""
        cleanup = effect_state()
        calls: list[int] = []

        cleanup.register(lambda: calls.append(1))
        cleanup.register(lambda: calls.append(2))
        cleanup.cleanup()

        assert calls == [1, 2]
        assert len(cleanup._cleanup_funcs) == 0
