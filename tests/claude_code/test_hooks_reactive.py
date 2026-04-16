"""
Tests for hooks/reactive.py - ReactiveState and reactive().
"""

from __future__ import annotations

import pytest

from src.claude_code.hooks.reactive import ReactiveState, ReactiveBinding, reactive


class TestReactiveState:
    """Tests for ReactiveState."""

    def test_initial_value(self) -> None:
        """ReactiveState starts with the provided value."""
        state = ReactiveState[int](42)
        assert state.value == 42

    def test_set_triggers_subscribers(self) -> None:
        """Setting value notifies subscribers."""
        state = ReactiveState(0)
        calls: list[int] = []

        unsub = state.subscribe(lambda: calls.append(state.value))
        state.value = 5
        assert calls == [5]
        unsub()

    def test_set_same_value_no_notify(self) -> None:
        """Setting same value does not notify."""
        state = ReactiveState(42)
        calls: list = []

        unsub = state.subscribe(lambda: calls.append(1))
        state.value = 42  # same value
        assert len(calls) == 0
        unsub()

    def test_multiple_subscribers(self) -> None:
        """Multiple subscribers all receive notifications."""
        state = ReactiveState(0)
        calls_a: list[int] = []
        calls_b: list[int] = []

        unsub_a = state.subscribe(lambda: calls_a.append(state.value))
        unsub_b = state.subscribe(lambda: calls_b.append(state.value))

        state.value = 10
        assert calls_a == [10]
        assert calls_b == [10]

        unsub_a()
        unsub_b()

    def test_unsubscribe_works(self) -> None:
        """Unsubscribe stops notifications."""
        state = ReactiveState(0)
        calls: list = []

        unsub = state.subscribe(lambda: calls.append(1))
        unsub()
        state.value = 5
        assert len(calls) == 0

    def test_version_increments(self) -> None:
        """Version increments on each change."""
        state = ReactiveState(0)
        assert state.version == 0
        state.value = 1
        assert state.version == 1
        state.value = 2
        assert state.version == 2

    def test_initial_none_value(self) -> None:
        """ReactiveState can be initialized with None."""
        state: ReactiveState[str | None] = ReactiveState(None)
        assert state.value is None


class TestReactive:
    """Tests for the reactive() composable."""

    def test_returns_value_and_setter(self) -> None:
        """reactive() returns (value, setter) tuple."""
        val, set_val = reactive(0)
        assert val == 0
        set_val(5)
        # Note: The returned value is a snapshot, set_val modifies the state object
        # The actual value change is reflected in the state
        assert val == 0  # Snapshot not updated (expected)


class TestReactiveBinding:
    """Tests for ReactiveBinding."""

    def test_attach_and_detach(self) -> None:
        """ReactiveBinding can attach and detach."""
        state = ReactiveState(0)

        class MockComponent:
            def __init__(self) -> None:
                self.updated_with: list[str] = []

            def update(self, s: str) -> None:
                self.updated_with.append(s)

        component = MockComponent()
        binding = ReactiveBinding(component, state, lambda: f"val={state.value}")

        assert binding._unsub is None
        binding.attach()
        assert binding._unsub is not None  # subscribed

        state.value = 99
        assert "val=99" in component.updated_with

        binding.detach()
        assert binding._unsub is None
