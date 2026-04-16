"""Suspend/resume functionality for Claude Code.

Handles SIGTSTP signal to suspend the running process and resume later,
similar to Ctrl+Z in a terminal.

TypeScript equivalent: src/cli/suspend.ts
"""

from __future__ import annotations

import os
import signal
import sys
from collections.abc import Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# Suspend State
# =============================================================================


class SuspendManager:
    """Manages process suspension and resumption.

    Handles SIGTSTP signal to suspend the REPL and return control
    to the shell. On resume (typically via `fg` or `bg` in shell),
    the process continues from where it left off.

    TypeScript equivalent: src/cli/suspend.ts
    """

    def __init__(
        self,
        on_suspend: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the suspend manager.

        Args:
            on_suspend: Optional callback when suspending.
            on_resume: Optional callback when resuming.
        """
        self._on_suspend = on_suspend
        self._on_resume = on_resume
        self._is_suspended = False
        self._original_sigstsp_handler: Any = None

    def setup(self) -> None:
        """Set up the SIGTSTP signal handler.

        Replaces the default terminal stop signal handler with our custom
        handler that invokes the suspend flow.
        """
        self._original_sigstsp_handler = signal.signal(
            signal.SIGTSTP, self._handle_sigtstp
        )

    def restore(self) -> None:
        """Restore the original SIGTSTP handler.

        Should be called when shutting down the REPL.
        """
        if self._original_sigstsp_handler is not None:
            signal.signal(signal.SIGTSTP, self._original_sigstsp_handler)
            self._original_sigstsp_handler = None

    def _handle_sigtstp(
        self, signum: int, frame: object | None
    ) -> None:
        """Handle SIGTSTP signal.

        Args:
            signum: Signal number (should be SIGTSTP).
            frame: Current stack frame.
        """
        self._is_suspended = True

        # Call optional suspend callback
        if self._on_suspend:
            self._on_suspend()

        # Send ourselves a SIGSTOP (which actually suspends the process)
        # Then restore the handler so we can be resumed
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGSTOP)

    def resume(self) -> None:
        """Resume from a suspended state.

        Called automatically when the process receives SIGCONT after being
        stopped, or can be called manually.
        """
        if not self._is_suspended:
            return

        self._is_suspended = False

        # Reinstall the signal handler
        signal.signal(signal.SIGTSTP, self._handle_sigtstp)

        # Call optional resume callback
        if self._on_resume:
            self._on_resume()

    @property
    def is_suspended(self) -> bool:
        """Check if currently suspended.

        Returns:
            True if suspended.
        """
        return self._is_suspended


# =============================================================================
# Global Suspend Manager
# =============================================================================


_suspend_manager: SuspendManager | None = None


def get_suspend_manager() -> SuspendManager:
    """Get the global suspend manager.

    Returns:
        The global SuspendManager instance.
    """
    global _suspend_manager
    if _suspend_manager is None:
        _suspend_manager = SuspendManager()
    return _suspend_manager


def setup_suspend(
    on_suspend: Callable[[], None] | None = None,
    on_resume: Callable[[], None] | None = None,
) -> SuspendManager:
    """Set up the global suspend manager.

    Args:
        on_suspend: Optional callback when suspending.
        on_resume: Optional callback when resuming.

    Returns:
        The configured SuspendManager.
    """
    global _suspend_manager
    _suspend_manager = SuspendManager(
        on_suspend=on_suspend,
        on_resume=on_resume,
    )
    _suspend_manager.setup()
    return _suspend_manager


def teardown_suspend() -> None:
    """Tear down the global suspend manager."""
    global _suspend_manager
    if _suspend_manager is not None:
        _suspend_manager.restore()
        _suspend_manager = None


# =============================================================================
# SIGCONT Handler (for auto-resume)
# =============================================================================


def _handle_sigcont(signum: int, frame: object | None) -> None:
    """Handle SIGCONT signal (received when resuming from stop).

    Args:
        signum: Signal number (should be SIGCONT).
        frame: Current stack frame.
    """
    global _suspend_manager
    if _suspend_manager is not None:
        _suspend_manager.resume()


# Install SIGCONT handler at module load
if hasattr(signal, "SIGCONT"):
    with suppress(ValueError, OSError):
        signal.signal(signal.SIGCONT, _handle_sigcont)


# =============================================================================
# TTY Control
# =============================================================================


def is_interactive() -> bool:
    """Check if running in an interactive terminal.

    Returns:
        True if stdin is a TTY and the terminal is interactive.
    """
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def suspend_process() -> None:
    """Suspend the current process.

    Sends SIGTSTP to the current process, which triggers the suspend flow.
    This is equivalent to pressing Ctrl+Z in an interactive terminal.
    """
    if not is_interactive():
        # Don't try to suspend in non-interactive mode
        return

    with suppress(OSError):
        os.kill(os.getpid(), signal.SIGTSTP)


def send_to_background() -> int:
    """Send the process to background (like Ctrl+Z then 'bg').

    Returns:
        0 on success, -1 on failure.
    """
    if not is_interactive():
        return -1

    try:
        # Get the process group
        pid = os.getpid()
        pgid = os.getpgid(pid)

        # Send SIGSTOP to the process group (this suspends)
        os.killpg(pgid, signal.SIGSTOP)
        return 0
    except OSError:
        return -1
