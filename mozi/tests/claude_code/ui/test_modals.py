"""Tests for UI modal system."""

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

    def test_default_values(self) -> None:
        """ModalResult has correct defaults."""
        result = ModalResult()
        assert result.action == "cancel"
        assert result.value is None

    def test_is_confirmed(self) -> None:
        """is_confirmed works."""
        result = ModalResult(action="confirm")
        assert result.is_confirmed() is True
        result.action = "cancel"
        assert result.is_confirmed() is False

    def test_is_cancelled(self) -> None:
        """is_cancelled works."""
        result = ModalResult(action="cancel")
        assert result.is_cancelled() is True
        result.action = "confirm"
        assert result.is_cancelled() is False


class TestModalOptions:
    """Tests for ModalOptions."""

    def test_default_values(self) -> None:
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


class TestModalState:
    """Tests for ModalState."""

    def test_creation(self) -> None:
        """ModalState can be created."""
        modal = ModalState(modal_id="modal-1", title="Test Modal")
        assert modal.modal_id == "modal-1"
        assert modal.title == "Test Modal"
        assert modal.is_open is False
        assert modal.result is None

    def test_open_close(self) -> None:
        """open and close work."""
        modal = ModalState(modal_id="modal-1", title="Test")
        assert modal.is_open is False
        modal.open()
        assert modal.is_open is True
        modal.close()
        assert modal.is_open is False

    def test_close_with_result(self) -> None:
        """close passes result to callback."""
        results: list[ModalResult] = []

        def callback(result: ModalResult) -> None:
            results.append(result)

        modal = ModalState(modal_id="modal-1", title="Test")
        modal.result_callback = callback
        modal.open()
        modal.close(ModalResult(action="confirm", value="test"))
        assert len(results) == 1
        assert results[0].action == "confirm"
        assert results[0].value == "test"

    def test_confirm(self) -> None:
        """confirm works correctly."""
        modal = ModalState(modal_id="modal-1", title="Test")
        results: list[ModalResult] = []

        def callback(result: ModalResult) -> None:
            results.append(result)

        modal.result_callback = callback
        modal.confirm(value="yes")
        assert len(results) == 1
        assert results[0].is_confirmed()

    def test_cancel(self) -> None:
        """cancel works correctly."""
        modal = ModalState(modal_id="modal-1", title="Test")
        results: list[ModalResult] = []

        def callback(result: ModalResult) -> None:
            results.append(result)

        modal.result_callback = callback
        modal.cancel()
        assert len(results) == 1
        assert results[0].is_cancelled()

    def test_set_get_data(self) -> None:
        """set_data and get_data work."""
        modal = ModalState(modal_id="modal-1", title="Test")
        modal.set_data("key1", "value1")
        assert modal.get_data("key1") == "value1"
        assert modal.get_data("key2", "default") == "default"


class TestModalManager:
    """Tests for ModalManager."""

    def setup_method(self) -> None:
        """Reset modal manager before each test."""
        reset_modal_manager()

    def test_push(self) -> None:
        """push creates and opens a modal."""
        manager = ModalManager()
        modal = manager.push(title="Test Modal")
        assert modal.title == "Test Modal"
        assert modal.is_open is True
        assert manager.stack_size == 1
        assert manager.is_active() is True

    def test_pop(self) -> None:
        """pop removes top modal."""
        manager = ModalManager()
        manager.push(title="Modal 1")
        manager.push(title="Modal 2")
        assert manager.stack_size == 2
        popped = manager.pop()
        assert popped is not None
        assert popped.title == "Modal 2"
        assert manager.stack_size == 1

    def test_pop_empty_stack(self) -> None:
        """pop on empty stack returns None."""
        manager = ModalManager()
        popped = manager.pop()
        assert popped is None

    def test_pop_with_result(self) -> None:
        """pop can pass a result."""
        manager = ModalManager()
        manager.push(title="Modal 1")
        results: list[ModalResult] = []
        manager._modals[0].result_callback = lambda r: results.append(r)
        manager.pop(ModalResult(action="confirm"))
        assert len(results) == 1
        assert results[0].action == "confirm"

    def test_dismiss_top(self) -> None:
        """dismiss_top works."""
        manager = ModalManager()
        manager.push(title="Modal 1")
        manager.push(title="Modal 2")
        result = manager.dismiss_top(action="confirm", value="yes")
        assert result is True
        assert manager.stack_size == 1

    def test_dismiss_top_empty(self) -> None:
        """dismiss_top on empty returns False."""
        manager = ModalManager()
        result = manager.dismiss_top()
        assert result is False

    def test_dismiss_all(self) -> None:
        """dismiss_all works."""
        manager = ModalManager()
        manager.push(title="Modal 1")
        manager.push(title="Modal 2")
        manager.push(title="Modal 3")
        count = manager.dismiss_all()
        assert count == 3
        assert manager.is_empty()

    def test_get_top(self) -> None:
        """get_top returns top modal."""
        manager = ModalManager()
        manager.push(title="Modal 1")
        manager.push(title="Modal 2")
        top = manager.get_top()
        assert top is not None
        assert top.title == "Modal 2"

    def test_get_top_empty(self) -> None:
        """get_top on empty returns None."""
        manager = ModalManager()
        assert manager.get_top() is None

    def test_get_all(self) -> None:
        """get_all returns all modals."""
        manager = ModalManager()
        manager.push(title="Modal 1")
        manager.push(title="Modal 2")
        all_modals = manager.get_all()
        assert len(all_modals) == 2
        assert all_modals[0].title == "Modal 1"
        assert all_modals[1].title == "Modal 2"

    def test_get_visible(self) -> None:
        """get_visible returns only open modals."""
        manager = ModalManager()
        modal1 = manager.push(title="Modal 1")
        modal2 = manager.push(title="Modal 2")
        # Manually close modal1
        modal1.close()
        visible = manager.get_visible()
        assert len(visible) == 1
        assert visible[0].title == "Modal 2"

    def test_is_active(self) -> None:
        """is_active works."""
        manager = ModalManager()
        assert manager.is_active() is False
        manager.push(title="Modal")
        assert manager.is_active() is True

    def test_is_empty(self) -> None:
        """is_empty works."""
        manager = ModalManager()
        assert manager.is_empty() is True
        manager.push(title="Modal")
        assert manager.is_empty() is False

    def test_find_by_id(self) -> None:
        """find_by_id works."""
        manager = ModalManager()
        modal = manager.push(title="Modal")
        found = manager.find_by_id(modal.modal_id)
        assert found is modal
        assert manager.find_by_id("nonexistent") is None

    def test_find_by_type(self) -> None:
        """find_by_type works."""
        manager = ModalManager()
        manager.push(title="Confirm", options=ModalOptions(modal_type=ModalType.CONFIRM))
        manager.push(title="Info", options=ModalOptions(modal_type=ModalType.INFO))
        found = manager.find_by_type(ModalType.CONFIRM)
        assert len(found) == 1
        assert found[0].title == "Confirm"

    def test_on_stack_change_callback(self) -> None:
        """on_stack_change callback is called."""
        manager = ModalManager()
        changes: list[list[ModalState]] = []

        def on_change(modals: list[ModalState]) -> None:
            changes.append(list(modals))

        manager.set_on_stack_change(on_change)
        manager.push(title="Modal 1")
        assert len(changes) == 1
        assert len(changes[0]) == 1
        manager.push(title="Modal 2")
        assert len(changes) == 2

    def test_on_any_modal_open_close_callbacks(self) -> None:
        """on_any_modal_open and on_any_modal_close work."""
        manager = ModalManager()
        opened: list[int] = []
        closed: list[int] = []

        manager.set_on_any_modal_open(lambda: opened.append(1))
        manager.set_on_any_modal_close(lambda: closed.append(1))

        manager.push(title="Modal")
        assert opened == [1]
        manager.pop()
        assert closed == [1]

    def test_callback_on_any_modal_open_called_every_push(self) -> None:
        """on_any_modal_open is called on every push."""
        manager = ModalManager()
        opened: list[int] = []

        def on_open() -> None:
            opened.append(1)

        manager.set_on_any_modal_open(on_open)
        manager.push(title="Modal 1")
        manager.push(title="Modal 2")
        # Called on every push
        assert len(opened) == 2


class TestGlobalFunctions:
    """Tests for global modal helper functions."""

    def setup_method(self) -> None:
        """Reset modal manager before each test."""
        reset_modal_manager()

    def test_push_modal(self) -> None:
        """push_modal uses global manager."""
        modal = push_modal(title="Test")
        assert modal.title == "Test"
        assert is_modal_active() is True

    def test_pop_modal(self) -> None:
        """pop_modal uses global manager."""
        push_modal(title="Test")
        popped = pop_modal()
        assert popped is not None
        assert popped.title == "Test"

    def test_dismiss_top_function(self) -> None:
        """dismiss_top uses global manager."""
        push_modal(title="Test")
        result = dismiss_top(action="confirm")
        assert result is True
        assert is_modal_active() is False

    def test_dismiss_all_function(self) -> None:
        """dismiss_all uses global manager."""
        push_modal(title="Test 1")
        push_modal(title="Test 2")
        count = dismiss_all()
        assert count == 2
        assert is_modal_active() is False

    def test_get_modal_manager(self) -> None:
        """get_modal_manager returns singleton."""
        mgr1 = get_modal_manager()
        mgr2 = get_modal_manager()
        assert mgr1 is mgr2
