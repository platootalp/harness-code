"""
Modal system for Claude Code TUI.

Provides a modal overlay system that manages dialog stacking, focus trapping,
and background interaction prevention.

TypeScript equivalents: context/modalContext.tsx, design-system/Dialog.tsx
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Modal Types
# =============================================================================


class ModalType(StrEnum):
    """Types of modals."""

    CONFIRM = "confirm"
    SELECTION = "selection"
    INPUT = "input"
    SEARCH = "search"
    SETTINGS = "settings"
    PERMISSION = "permission"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CUSTOM = "custom"


class ModalPriority(StrEnum):
    """Modal stacking priority."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Modal Result
# =============================================================================


@dataclass
class ModalResult:
    """Result returned when a modal is dismissed."""

    action: str = "cancel"
    value: Any = None

    def is_confirmed(self) -> bool:
        """Check if the result is a confirmation."""
        return self.action == "confirm"

    def is_cancelled(self) -> bool:
        """Check if the result is a cancellation."""
        return self.action == "cancel"


# =============================================================================
# Modal Options
# =============================================================================


@dataclass
class ModalOptions:
    """Options for modal behavior.

    Attributes:
        modal_type: The type of modal.
        priority: Stacking priority.
        dismissable: Whether clicking outside dismisses the modal.
        escape_closes: Whether Escape key closes the modal.
        enter_confirms: Whether Enter key confirms the modal.
        trap_focus: Whether focus is trapped within the modal.
        block_background: Whether background interaction is blocked.
        animate: Whether the modal should animate open/close.
    """

    modal_type: ModalType = ModalType.CUSTOM
    priority: ModalPriority = ModalPriority.NORMAL
    dismissable: bool = True
    escape_closes: bool = True
    enter_confirms: bool = False
    trap_focus: bool = True
    block_background: bool = True
    animate: bool = True


# =============================================================================
# Modal State
# =============================================================================


@dataclass
class ModalState:
    """State for a single modal instance.

    Attributes:
        modal_id: Unique identifier for this modal.
        title: The modal title.
        content: The modal content/children.
        options: Modal behavior options.
        is_open: Whether the modal is currently visible.
        result_callback: Callback invoked with the result when modal closes.
    """

    modal_id: str
    title: str
    content: Any = None
    options: ModalOptions = field(default_factory=ModalOptions)
    is_open: bool = False
    result_callback: Callable[[ModalResult], None] | None = field(default=None, repr=False)
    result: ModalResult | None = field(default=None, repr=False)
    _data: dict[str, Any] = field(default_factory=dict)

    def open(self) -> None:
        """Open the modal."""
        self.is_open = True

    def close(self, result: ModalResult | None = None) -> None:
        """Close the modal with an optional result.

        Args:
            result: The result to pass to the callback.
        """
        self.is_open = False
        if result is None:
            result = ModalResult(action="cancel")
        self.result = result
        if self.result_callback:
            self.result_callback(result)

    def confirm(self, value: Any = None) -> None:
        """Close the modal with a confirm result.

        Args:
            value: Optional value to pass with the result.
        """
        self.close(ModalResult(action="confirm", value=value))

    def cancel(self) -> None:
        """Close the modal with a cancel result."""
        self.close(ModalResult(action="cancel"))

    def set_data(self, key: str, value: Any) -> None:
        """Store arbitrary data on the modal.

        Args:
            key: Data key.
            value: Data value.
        """
        self._data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from the modal.

        Args:
            key: Data key.
            default: Default value if key not found.

        Returns:
            The stored value or default.
        """
        return self._data.get(key, default)


# =============================================================================
# Modal Manager
# =============================================================================


class ModalManager:
    """Manages the modal stack and overlay state.

    Handles pushing/popping modals, coordinating focus, and
    blocking background interaction when modals are active.

    TypeScript equivalent: ModalContext overlay management.
    """

    def __init__(self) -> None:
        """Initialize the modal manager."""
        self._modals: list[ModalState] = []
        self._next_id: int = 1
        self._on_stack_change: Callable[[list[ModalState]], None] | None = None
        self._on_any_modal_open: Callable[[], None] | None = None
        self._on_any_modal_close: Callable[[], None] | None = None

    def push(
        self,
        title: str,
        content: Any = None,
        options: ModalOptions | None = None,
        result_callback: Callable[[ModalResult], None] | None = None,
    ) -> ModalState:
        """Push a new modal onto the stack.

        Args:
            title: The modal title.
            content: The modal content.
            options: Modal behavior options.
            result_callback: Callback when modal is dismissed.

        Returns:
            The created ModalState.
        """
        modal = ModalState(
            modal_id=f"modal_{self._next_id}",
            title=title,
            content=content,
            options=options or ModalOptions(),
            result_callback=result_callback,
        )
        self._next_id += 1
        self._modals.append(modal)
        modal.open()
        self._notify_stack_change()
        if self._on_any_modal_open:
            self._on_any_modal_open()
        return modal

    def pop(self, result: ModalResult | None = None) -> ModalState | None:
        """Pop the top modal from the stack.

        Args:
            result: Optional result to pass to the callback.

        Returns:
            The popped modal, or None if stack is empty.
        """
        if not self._modals:
            return None
        modal = self._modals.pop()
        modal.close(result)
        self._notify_stack_change()
        if self._on_any_modal_close:
            self._on_any_modal_close()
        return modal

    def dismiss_top(self, action: str = "cancel", value: Any = None) -> bool:
        """Dismiss the top modal.

        Args:
            action: The action string ("confirm", "cancel", etc.).
            value: Optional value to pass with the result.

        Returns:
            True if a modal was dismissed, False if stack was empty.
        """
        result = ModalResult(action=action, value=value)
        popped = self.pop(result)
        return popped is not None

    def dismiss_all(self, action: str = "cancel", value: Any = None) -> int:
        """Dismiss all modals in the stack.

        Args:
            action: The action string for all results.
            value: Optional value to pass with all results.

        Returns:
            The number of modals dismissed.
        """
        count = 0
        result = ModalResult(action=action, value=value)
        while self._modals:
            modal = self._modals.pop()
            modal.close(result)
            count += 1
        if count > 0:
            self._notify_stack_change()
            if self._on_any_modal_close:
                self._on_any_modal_close()
        return count

    def get_top(self) -> ModalState | None:
        """Get the topmost modal.

        Returns:
            The top modal, or None if stack is empty.
        """
        if self._modals:
            return self._modals[-1]
        return None

    def get_all(self) -> list[ModalState]:
        """Get all modals in the stack.

        Returns:
            List of all modal states, bottom to top.
        """
        return list(self._modals)

    def get_visible(self) -> list[ModalState]:
        """Get all visible (open) modals.

        Returns:
            List of open modal states.
        """
        return [m for m in self._modals if m.is_open]

    def is_active(self) -> bool:
        """Check if any modal is active.

        Returns:
            True if there are open modals.
        """
        return any(m.is_open for m in self._modals)

    def is_empty(self) -> bool:
        """Check if the modal stack is empty.

        Returns:
            True if no modals in stack.
        """
        return len(self._modals) == 0

    @property
    def stack_size(self) -> int:
        """Get the number of modals in the stack."""
        return len(self._modals)

    def find_by_id(self, modal_id: str) -> ModalState | None:
        """Find a modal by its ID.

        Args:
            modal_id: The modal ID to search for.

        Returns:
            The modal if found, None otherwise.
        """
        for modal in self._modals:
            if modal.modal_id == modal_id:
                return modal
        return None

    def find_by_type(self, modal_type: ModalType) -> list[ModalState]:
        """Find all modals of a specific type.

        Args:
            modal_type: The modal type to search for.

        Returns:
            List of matching modals.
        """
        return [m for m in self._modals if m.options.modal_type == modal_type]

    def set_on_stack_change(
        self, callback: Callable[[list[ModalState]], None]
    ) -> None:
        """Set a callback for stack changes.

        Args:
            callback: Function called when the stack changes.
        """
        self._on_stack_change = callback

    def set_on_any_modal_open(self, callback: Callable[[], None]) -> None:
        """Set a callback for any modal opening.

        Args:
            callback: Function called when any modal opens.
        """
        self._on_any_modal_open = callback

    def set_on_any_modal_close(self, callback: Callable[[], None]) -> None:
        """Set a callback for any modal closing.

        Args:
            callback: Function called when any modal closes.
        """
        self._on_any_modal_close = callback

    def _notify_stack_change(self) -> None:
        """Notify listeners of stack changes."""
        if self._on_stack_change:
            self._on_stack_change(list(self._modals))


# =============================================================================
# Global Modal Manager Instance
# =============================================================================

_modal_manager: ModalManager | None = None


def get_modal_manager() -> ModalManager:
    """Get the global modal manager instance.

    Returns:
        The global ModalManager.
    """
    global _modal_manager
    if _modal_manager is None:
        _modal_manager = ModalManager()
    return _modal_manager


def reset_modal_manager() -> None:
    """Reset the global modal manager (for testing)."""
    global _modal_manager
    _modal_manager = ModalManager()


def push_modal(
    title: str,
    content: Any = None,
    options: ModalOptions | None = None,
    result_callback: Callable[[ModalResult], None] | None = None,
) -> ModalState:
    """Push a modal using the global manager.

    Args:
        title: The modal title.
        content: The modal content.
        options: Modal behavior options.
        result_callback: Callback when modal is dismissed.

    Returns:
        The created ModalState.
    """
    return get_modal_manager().push(title, content, options, result_callback)


def pop_modal(result: ModalResult | None = None) -> ModalState | None:
    """Pop the top modal from the global manager.

    Args:
        result: Optional result to pass.

    Returns:
        The popped modal.
    """
    return get_modal_manager().pop(result)


def is_modal_active() -> bool:
    """Check if any modal is active in the global manager.

    Returns:
        True if there are open modals.
    """
    return get_modal_manager().is_active()


def dismiss_top(action: str = "cancel", value: Any = None) -> bool:
    """Dismiss the top modal in the global manager.

    Args:
        action: The action type for dismissal.
        value: Optional value to pass to the result.

    Returns:
        True if a modal was dismissed, False if stack was empty.
    """
    return get_modal_manager().dismiss_top(action, value)


def dismiss_all(action: str = "cancel", value: Any = None) -> int:
    """Dismiss all modals in the global manager.

    Args:
        action: The action type for dismissal.
        value: Optional value to pass to the result.

    Returns:
        Number of modals dismissed.
    """
    return get_modal_manager().dismiss_all(action, value)
