"""
reactive.py - Reactive state variable for Textual components.

Provides a reactive state wrapper that integrates with Textual's @reactive
decorator pattern while supporting global state subscriptions.

Migrated from src/hooks/useReactive.ts pattern.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from textual.app import Component

T = TypeVar("T")


@dataclass
class ReactiveState(Generic[T]):
    """
    Holds a reactive value with change subscription support.

    Similar to React's useState + useSyncExternalStore pattern.
    When used with Textual widgets, can automatically update display.

    Example:
        # Standalone usage
        count = ReactiveState(0)
        print(count.value)  # 0
        count.value = 1
        print(count.value)  # 1

        # With subscription
        def on_change():
            print(f"Changed to {count.value}")

        unsub = count.subscribe(on_change)
        count.value = 2  # prints: Changed to 2
        unsub()
    """

    _value: T = field(default=None)  # type: ignore[assignment]
    _version: int = 0
    _subscribers: list[Callable[[], None]] = field(default_factory=list)

    @property
    def value(self) -> T:
        """Get the current value."""
        return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set the value and notify subscribers if changed."""
        if new_value == self._value:
            return
        self._value = new_value
        self._version += 1
        self._notify()

    def _notify(self) -> None:
        """Notify all subscribers of a change."""
        for cb in self._subscribers:
            with contextlib.suppress(Exception):
                cb()

    def subscribe(self, cb: Callable[[], None]) -> Callable[[], None]:
        """Subscribe to value changes. Returns unsubscribe function."""
        self._subscribers.append(cb)

        def unsubscribe() -> None:
            self._subscribers.remove(cb)

        return unsubscribe

    @property
    def version(self) -> int:
        """Current version for cache invalidation."""
        return self._version


def reactive(
    default_value: T,
    *,
    layout: bool = False,
    repaint: bool = True,
    init: bool = True,
) -> tuple[T, Callable[[T], None]]:
    """
    Create a reactive state variable.

    This is a composable function meant to be called during widget initialization.
    For Textual widgets, prefer the @reactive decorator on widget class attributes.

    Args:
        default_value: Initial value for the reactive state.
        layout: If True, triggers layout recomputation on change.
        repaint: If True, triggers repaint on change.
        init: If True, runs initialization.

    Returns:
        Tuple of (current_value, setter_function).

    Example:
        count, set_count = reactive(0)
        set_count(5)
        print(count)  # 5
    """
    state = ReactiveState[T](default_value)
    return state.value, lambda v: setattr(state, "value", v)


class ReactiveBinding(Generic[T]):
    """
    Binds a ReactiveState to a Textual component for automatic display updates.

    When the reactive value changes, the component is automatically updated.

    Example:
        class MyWidget(Static):
            count = ReactiveState(0)

            def __init__(self):
                super().__init__()
                self._binding = ReactiveBinding(self, self.count, self._render)
                self._binding.attach()

            def _render(self) -> str:
                return f"Count: {self.count.value}"

            def on_unmount(self):
                self._binding.detach()
    """

    def __init__(
        self,
        component: Component,
        state: ReactiveState[T],
        render_fn: Callable[[], str],
    ) -> None:
        self._component = component
        self._state = state
        self._render_fn = render_fn
        self._unsub: Callable[[], None] | None = None

    def attach(self) -> None:
        """Start listening for changes and render initial value."""
        self._unsub = self._state.subscribe(self._on_change)

    def detach(self) -> None:
        """Stop listening for changes."""
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def _on_change(self) -> None:
        """Called when the reactive value changes."""
        with contextlib.suppress(Exception):
            self._component.update(self._render_fn())
