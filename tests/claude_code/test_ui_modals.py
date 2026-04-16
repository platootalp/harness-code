"""
Tests for ui/modals.py - Modal system.
"""

from __future__ import annotations

import pytest

from claude_code.ui.modals import (
    ModalManager,
    ModalOptions,
    ModalPriority,
    ModalResult,
    ModalState,
    ModalType,
    dismiss_all,
    dismiss_top,
    get_modal_manager,
    is_modal_active,
    pop_modal,
    push_modal,
    reset_modal_manager,
)


class TestModalResult:
    """Tests for ModalResult."""

    def test_default_action_is_cancel(self) -> None:
        """ModalResult defaults to cancel action."""
        result = ModalResult()
        assert result.action == "cancel"
        assert result.value is None

    def test_is_confirmed(self) -> None:
        """is_confirmed returns True for confirm action."""
        result = ModalResult(action="confirm", value="test")
        assert result.is_confirmed() is True
        assert result.is_cancelled() is False

    def test_is_cancelled(self) -> None:
        """is_cancelled returns True for cancel action."""
        result = ModalResult(action="cancel")
        assert result.is_cancelled() is True
        assert result.is_confirmed() is False


class TestModalOptions:
    """Tests for ModalOptions."""

    def test_default_options(self) -> None:
        """ModalOptions has correct defaults."""
        opts = ModalOptions()
        assert opts.modal_type == ModalType.CUSTOM
        assert opts.priority == ModalPriority.NORMAL
        assert opts.dismissable is True
        assert opts.escape_closes is True
        assert opts.enter_confirms is False
        assert opts.trap_focus is True
        assert opts.block_background is True
        assert opts.animate is True

    def test_custom_options(self) -> None:
        """ModalOptions accepts custom values."""
        opts = ModalOptions(
            modal_type=ModalType.SEARCH,
            priority=ModalPriority.HIGH,
            dismissable=False,
        )
        assert opts.modal_type == ModalType.SEARCH
        assert opts.priority == ModalPriority.HIGH
        assert opts.dismissable is False


class TestModalState:
    """Tests for ModalState."""

    def test_initial_state(self) -> None:
        """ModalState initializes correctly."""
        modal = ModalState(modal_id="test_1", title="Test Modal")
        assert modal.modal_id == "test_1"
        assert modal.title == "Test Modal"
        assert modal.is_open is False
        assert modal.result_callback is None

    def test_open_and_close(self) -> None:
        """open() and close() manage is_open state."""
        modal = ModalState(modal_id="test", title="Test")
        modal.open()
        assert modal.is_open is True
        modal.close(ModalResult(action="confirm"))
        assert modal.is_open is False
        assert modal.result.action == "confirm"

    def test_confirm(self) -> None:
        """confirm() closes with confirm result."""
        modal = ModalState(modal_id="test", title="Test")
        modal.confirm("my_value")
        assert modal.is_open is False
        assert modal.result.action == "confirm"
        assert modal.result.value == "my_value"

    def test_cancel(self) -> None:
        """cancel() closes with cancel result."""
        modal = ModalState(modal_id="test", title="Test")
        modal.cancel()
        assert modal.is_open is False
        assert modal.result.action == "cancel"

    def test_result_callback(self) -> None:
        """Result callback is called on close."""
        results: list[ModalResult] = []

        def callback(result: ModalResult) -> None:
            results.append(result)

        modal = ModalState(modal_id="test", title="Test", result_callback=callback)
        modal.confirm("value")
        assert len(results) == 1
        assert results[0].value == "value"

    def test_data_storage(self) -> None:
        """set_data and get_data work correctly."""
        modal = ModalState(modal_id="test", title="Test")
        modal.set_data("key1", "value1")
        modal.set_data("key2", 42)
        assert modal.get_data("key1") == "value1"
        assert modal.get_data("key2") == 42
        assert modal.get_data("missing", "default") == "default"


class TestModalManager:
    """Tests for ModalManager."""

    def test_push_creates_modal(self) -> None:
        """push() creates and opens a modal."""
        mgr = ModalManager()
        modal = mgr.push("Test Modal")
        assert modal.title == "Test Modal"
        assert modal.is_open is True
        assert mgr.stack_size == 1

    def test_push_increments_id(self) -> None:
        """Each push gets a unique ID."""
        mgr = ModalManager()
        m1 = mgr.push("A")
        m2 = mgr.push("B")
        m3 = mgr.push("C")
        assert m1.modal_id == "modal_1"
        assert m2.modal_id == "modal_2"
        assert m3.modal_id == "modal_3"

    def test_push_with_callback(self) -> None:
        """push() registers result callback."""
        results: list[ModalResult] = []
        mgr = ModalManager()
        mgr.push("Test", result_callback=lambda r: results.append(r))
        assert len(results) == 0
        mgr.dismiss_top("confirm", "val")
        assert len(results) == 1
        assert results[0].value == "val"

    def test_pop_removes_top(self) -> None:
        """pop() removes and closes the top modal."""
        mgr = ModalManager()
        mgr.push("A")
        modal_b = mgr.push("B")
        assert mgr.stack_size == 2
        popped = mgr.pop()
        assert popped is modal_b
        assert mgr.stack_size == 1

    def test_pop_empty_stack(self) -> None:
        """pop() on empty stack returns None."""
        mgr = ModalManager()
        assert mgr.pop() is None

    def test_pop_with_result(self) -> None:
        """pop() passes result to callback."""
        results: list[ModalResult] = []
        mgr = ModalManager()
        mgr.push("Test", result_callback=lambda r: results.append(r))
        mgr.pop(ModalResult(action="confirm", value="x"))
        assert results[0].value == "x"

    def test_dismiss_top(self) -> None:
        """dismiss_top() closes top modal with action."""
        mgr = ModalManager()
        mgr.push("Test")
        assert mgr.dismiss_top("cancel") is True
        assert mgr.is_empty() is True

    def test_dismiss_top_empty(self) -> None:
        """dismiss_top() on empty returns False."""
        mgr = ModalManager()
        assert mgr.dismiss_top() is False

    def test_dismiss_all(self) -> None:
        """dismiss_all() closes all modals."""
        mgr = ModalManager()
        mgr.push("A")
        mgr.push("B")
        mgr.push("C")
        count = mgr.dismiss_all("cancel")
        assert count == 3
        assert mgr.is_empty() is True

    def test_dismiss_all_empty(self) -> None:
        """dismiss_all() on empty returns 0."""
        mgr = ModalManager()
        assert mgr.dismiss_all() == 0

    def test_get_top(self) -> None:
        """get_top() returns the top modal."""
        mgr = ModalManager()
        assert mgr.get_top() is None
        mgr.push("A")
        mgr.push("B")
        assert mgr.get_top() is not None
        assert mgr.get_top().title == "B"

    def test_get_all(self) -> None:
        """get_all() returns all modals bottom to top."""
        mgr = ModalManager()
        m1 = mgr.push("A")
        m2 = mgr.push("B")
        all_modals = mgr.get_all()
        assert all_modals == [m1, m2]

    def test_get_visible(self) -> None:
        """get_visible() returns only open modals."""
        mgr = ModalManager()
        m1 = mgr.push("A")
        m2 = mgr.push("B")
        m2.close()  # close B but leave in stack
        visible = mgr.get_visible()
        assert visible == [m1]

    def test_is_active(self) -> None:
        """is_active() returns True when any modal is open."""
        mgr = ModalManager()
        assert mgr.is_active() is False
        mgr.push("Test")
        assert mgr.is_active() is True
        mgr.pop()
        assert mgr.is_active() is False

    def test_find_by_id(self) -> None:
        """find_by_id() locates a modal by ID."""
        mgr = ModalManager()
        m1 = mgr.push("A")
        mgr.push("B")
        found = mgr.find_by_id(m1.modal_id)
        assert found is m1
        assert mgr.find_by_id("nonexistent") is None

    def test_find_by_type(self) -> None:
        """find_by_type() finds modals of a specific type."""
        mgr = ModalManager()
        mgr.push("A", options=ModalOptions(modal_type=ModalType.CONFIRM))
        mgr.push("B", options=ModalOptions(modal_type=ModalType.SEARCH))
        mgr.push("C", options=ModalOptions(modal_type=ModalType.CONFIRM))
        found = mgr.find_by_type(ModalType.CONFIRM)
        assert len(found) == 2

    def test_on_stack_change_callback(self) -> None:
        """set_on_stack_change fires on push/pop."""
        events: list[int] = []

        def on_change(_: list[ModalState]) -> None:
            events.append(len(_))

        mgr = ModalManager()
        mgr.set_on_stack_change(on_change)
        mgr.push("A")
        mgr.push("B")
        mgr.pop()
        assert events == [1, 2, 1]

    def test_on_any_modal_open_close_callbacks(self) -> None:
        """open/close callbacks fire correctly."""
        opens: list[int] = []
        closes: list[int] = []

        mgr = ModalManager()
        mgr.set_on_any_modal_open(lambda: opens.append(1))
        mgr.set_on_any_modal_close(lambda: closes.append(1))
        mgr.push("A")
        mgr.push("B")
        mgr.pop()
        mgr.dismiss_all()
        assert opens == [1, 1]
        assert closes == [1, 1]


class TestGlobalModalFunctions:
    """Tests for global modal manager functions."""

    def setup_method(self) -> None:
        """Reset global manager before each test."""
        reset_modal_manager()

    def test_get_modal_manager_returns_same_instance(self) -> None:
        """get_modal_manager returns singleton."""
        m1 = get_modal_manager()
        m2 = get_modal_manager()
        assert m1 is m2

    def test_push_modal_uses_global(self) -> None:
        """push_modal() uses global manager."""
        modal = push_modal("Global Test")
        assert modal.title == "Global Test"
        assert is_modal_active() is True

    def test_pop_modal_uses_global(self) -> None:
        """pop_modal() uses global manager."""
        push_modal("Test")
        popped = pop_modal()
        assert popped is not None
        assert is_modal_active() is False

    def test_dismiss_top_global(self) -> None:
        """dismiss_top() uses global manager."""
        push_modal("Test")
        assert dismiss_top("confirm") is True
        assert is_modal_active() is False

    def test_dismiss_all_global(self) -> None:
        """dismiss_all() uses global manager."""
        push_modal("A")
        push_modal("B")
        count = dismiss_all("cancel")
        assert count == 2
        assert is_modal_active() is False
