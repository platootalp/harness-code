"""
effect.py - @effect decorator for async side-effects with dependency tracking.

Provides a decorator-based effect system for Python/Textual that replaces
React's useEffect. Effects run asynchronously and re-run when dependencies change.

Migrated from src/hooks/useEffect.ts pattern.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app_state_store import AppStateStore
    from .observable import AsyncObservable

logger = logging.getLogger(__name__)


@dataclass
class EffectCleanup:
    """Holds cleanup functions registered by an effect."""

    _cleanup_funcs: list[Callable[[], None]] = field(default_factory=list)

    def register(self, cleanup: Callable[[], None]) -> None:
        """Register a cleanup function to be called on cleanup or re-run."""
        self._cleanup_funcs.append(cleanup)

    def cleanup(self) -> None:
        """Run all registered cleanup functions and clear the list."""
        for func in self._cleanup_funcs:
            try:
                func()
            except Exception as e:
                logger.warning(f"Effect cleanup error: {e}")
        self._cleanup_funcs.clear()


EffectFunc = Callable[[], Awaitable[None] | None]
EffectDeps = list[Any] | None


def effect(
    deps: EffectDeps = None,
    *,
    on_mount: bool = False,
    store: AppStateStore | AsyncObservable | None = None,
) -> Callable[[EffectFunc], EffectFunc]:
    """
    Decorator for async side-effects with optional dependency tracking.

    Effects are async tasks that run in response to state changes or on mount.
    When deps are provided, the effect re-runs only when a dependency changes.

    Args:
        deps: List of dependency values. Effect re-runs when any dep changes.
              None = run on every trigger.
              [] = run once (only on_mount=True).
        on_mount: If True, run immediately when the decorated method is called.
        store: Optional store for dependency resolution (defaults to get_app_state).

    Returns:
        A decorator that wraps the async effect function.

    Example:
        class MyComponent:
            def __init__(self, store: AppStateStore):
                self.store = store
                self._effect = effect_state()

            @effect(deps=["settings"], on_mount=True, store=store)
            async def on_settings_change(self) -> None:
                settings = self.store.get()["settings"]
                await self.persist_settings(settings)

            def cleanup(self) -> None:
                self._effect.cleanup()

    Example (standalone):
        @effect(deps=None)
        async def log_changes() -> None:
            store = get_app_state()
            print(f"State changed: {store.get()}")

        log_changes()  # Immediately runs
    """

    def decorator(
        func: EffectFunc,
    ) -> EffectFunc:
        prev_deps: list[Any] = []
        cleanup = EffectCleanup()
        effect_store = store

        @wraps(func)
        async def run_effect() -> None:
            nonlocal prev_deps, effect_store

            if effect_store is None:
                try:
                    from .context import get_app_state

                    effect_store = get_app_state()
                except RuntimeError:
                    logger.debug("effect: no app state in context, skipping")
                    return

            if deps is None:
                # No dependency tracking - run every time
                await _run_async(func)
                return

            if deps == [] and on_mount:
                # Run once on mount
                prev_deps = []
                await _run_async(func)
                return

            # Check if deps changed
            resolved_deps = [_resolve_dep(d, effect_store) for d in deps]
            if resolved_deps != prev_deps:
                # Cleanup previous effect
                cleanup.cleanup()

                prev_deps = resolved_deps
                # Run the effect, handling both sync and async results
                try:
                    result = func()
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.warning(f"effect error: {e}")

        def trigger() -> asyncio.Task[None]:
            """Trigger the effect to run. Returns the scheduled task."""
            return asyncio.create_task(run_effect())

        # Store the trigger on the decorated function so callers can access it
        func.trigger = trigger  # type: ignore
        func._effect_cleanup = cleanup  # type: ignore

        return func

    return decorator


async def _run_async(func: EffectFunc) -> None:
    """Run an effect function, handling both sync and async results."""
    try:
        result = func()
        if asyncio.iscoroutine(result):
            await result
    except Exception as e:
        logger.warning(f"effect run error: {e}")


def _resolve_dep(dep: Any, store: Any) -> Any:
    """
    Resolve a dependency value.

    - If dep is a string and store has get(), treat it as a state key.
    - Otherwise, return the dep as-is.
    """
    if isinstance(dep, str) and hasattr(store, "get"):
        state = store.get()
        if isinstance(state, dict):
            return state.get(dep)
    return dep


def effect_state() -> EffectCleanup:
    """
    Create a shared cleanup tracker for multiple effects.

    Use this when a class has multiple @effect-decorated methods
    to share a single cleanup registry.

    Example:
        class MyWidget:
            def __init__(self, store):
                self.store = store
                self._effect = effect_state()

            @effect(deps=["count"], store=store)
            async def on_count_change(self):
                pass

            def cleanup(self):
                self._effect.cleanup()
    """
    return EffectCleanup()
