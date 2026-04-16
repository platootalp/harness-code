"""
Tests for cli/suspend.py - suspend/resume functionality.
"""

from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

import pytest

from claude_code.cli.suspend import (
    SuspendManager,
    get_suspend_manager,
    is_interactive,
    send_to_background,
    setup_suspend,
    suspend_process,
    teardown_suspend,
)


class TestSuspendManagerInit:
    """Tests for SuspendManager initialization."""

    def test_default_init(self) -> None:
        """SuspendManager initializes with correct defaults."""
        mgr = SuspendManager()
        assert mgr.is_suspended is False
        assert mgr._on_suspend is None
        assert mgr._on_resume is None

    def test_init_with_callbacks(self) -> None:
        """SuspendManager accepts on_suspend and on_resume callbacks."""
        on_suspend = MagicMock()
        on_resume = MagicMock()
        mgr = SuspendManager(on_suspend=on_suspend, on_resume=on_resume)
        assert mgr._on_suspend is on_suspend
        assert mgr._on_resume is on_resume
        assert mgr.is_suspended is False


class TestSuspendManagerSetupRestore:
    """Tests for setup and restore methods."""

    def test_setup_installs_handler(self) -> None:
        """setup() calls signal.signal with the handler."""
        mgr = SuspendManager()
        with patch("claude_code.cli.suspend.signal.signal") as mock_signal:
            mgr.setup()
            mock_signal.assert_called_once()
            args = mock_signal.call_args[0]
            assert args[0] == signal.SIGTSTP
            assert args[1] == mgr._handle_sigtstp

    def test_restore_installs_original_handler(self) -> None:
        """restore() reinstalls the original handler."""
        mgr = SuspendManager()
        original = MagicMock()
        with patch("claude_code.cli.suspend.signal.signal") as mock_signal:
            mgr.setup()
            mgr._original_sigstsp_handler = original
            mgr.restore()
            # Second call: signal.signal called with original handler
            last_call = mock_signal.call_args_list[-1]
            assert last_call[0][0] == signal.SIGTSTP
            assert last_call[0][1] == original
            assert mgr._original_sigstsp_handler is None

    def test_restore_noop_when_not_setup(self) -> None:
        """restore() is safe to call before setup()."""
        mgr = SuspendManager()
        mgr.restore()  # Should not raise
        assert mgr._original_sigstsp_handler is None


class TestSuspendManagerResume:
    """Tests for resume() method."""

    def test_resume_clears_suspended_flag(self) -> None:
        """resume() clears the is_suspended flag."""
        mgr = SuspendManager()
        mgr._is_suspended = True
        with patch("claude_code.cli.suspend.signal.signal"):
            mgr.resume()
        assert mgr.is_suspended is False

    def test_resume_installs_handler(self) -> None:
        """resume() reinstalls the SIGTSTP handler."""
        mgr = SuspendManager()
        mgr._is_suspended = True
        with patch("claude_code.cli.suspend.signal.signal") as mock_signal:
            mgr.resume()
            mock_signal.assert_called_once()
            args = mock_signal.call_args[0]
            assert args[1] == mgr._handle_sigtstp

    def test_resume_calls_callback(self) -> None:
        """resume() calls the on_resume callback."""
        on_resume = MagicMock()
        mgr = SuspendManager(on_resume=on_resume)
        mgr._is_suspended = True
        with patch("claude_code.cli.suspend.signal.signal"):
            mgr.resume()
        on_resume.assert_called_once()

    def test_resume_noop_when_not_suspended(self) -> None:
        """resume() does nothing when not suspended."""
        mgr = SuspendManager()
        on_resume = MagicMock()
        mgr._on_resume = on_resume
        with patch("claude_code.cli.suspend.signal.signal") as mock_signal:
            mgr.resume()
        on_resume.assert_not_called()
        mock_signal.assert_not_called()


class TestSuspendManagerHandleSigstp:
    """Tests for _handle_sigtstp behavior (mocked)."""

    def test_handle_sigtstp_sets_flag(self) -> None:
        """_handle_sigtstp sets is_suspended to True."""
        mgr = SuspendManager()
        with patch("claude_code.cli.suspend.signal.signal"), \
                patch("claude_code.cli.suspend.os.kill"):
            mgr._handle_sigtstp(20, None)
        assert mgr.is_suspended is True

    def test_handle_sigtstp_calls_suspend_callback(self) -> None:
        """_handle_sigtstp calls the on_suspend callback."""
        on_suspend = MagicMock()
        mgr = SuspendManager(on_suspend=on_suspend)
        with patch("claude_code.cli.suspend.signal.signal"), \
                patch("claude_code.cli.suspend.os.kill"):
            mgr._handle_sigtstp(20, None)
        on_suspend.assert_called_once()

    def test_handle_sigtstp_sends_sigstop(self) -> None:
        """_handle_sigtstp sends SIGSTOP to self."""
        mgr = SuspendManager()
        with patch("claude_code.cli.suspend.signal.signal"), \
                patch("claude_code.cli.suspend.os.kill") as mock_kill, \
                patch("claude_code.cli.suspend.os.getpid", return_value=12345):
            mgr._handle_sigtstp(20, None)
        mock_kill.assert_called()


class TestIsInteractive:
    """Tests for is_interactive()."""

    def test_is_interactive_true_when_both_tty(self) -> None:
        """is_interactive returns True when stdin and stdout are TTYs."""
        with patch("claude_code.cli.suspend.sys.stdin") as mock_stdin, \
                patch("claude_code.cli.suspend.sys.stdout") as mock_stdout:
            mock_stdin.isatty.return_value = True
            mock_stdout.isatty.return_value = True
            assert is_interactive() is True

    def test_is_interactive_false_when_stdin_not_tty(self) -> None:
        """is_interactive returns False when stdin is not a TTY."""
        with patch("claude_code.cli.suspend.sys.stdin") as mock_stdin, \
                patch("claude_code.cli.suspend.sys.stdout") as mock_stdout:
            mock_stdin.isatty.return_value = False
            mock_stdout.isatty.return_value = True
            assert is_interactive() is False

    def test_is_interactive_false_when_stdout_not_tty(self) -> None:
        """is_interactive returns False when stdout is not a TTY."""
        with patch("claude_code.cli.suspend.sys.stdin") as mock_stdin, \
                patch("claude_code.cli.suspend.sys.stdout") as mock_stdout:
            mock_stdin.isatty.return_value = True
            mock_stdout.isatty.return_value = False
            assert is_interactive() is False

    def test_is_interactive_false_on_attribute_error(self) -> None:
        """is_interactive returns False on AttributeError."""
        with patch("claude_code.cli.suspend.sys.stdin", None), \
                patch("claude_code.cli.suspend.sys.stdout", None):
            assert is_interactive() is False

    def test_is_interactive_false_on_value_error(self) -> None:
        """is_interactive returns False on ValueError."""
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdin.isatty.side_effect = ValueError("closed")
        mock_stdout.isatty.side_effect = ValueError("closed")
        with patch("claude_code.cli.suspend.sys.stdin", mock_stdin), \
                patch("claude_code.cli.suspend.sys.stdout", mock_stdout):
            assert is_interactive() is False


class TestSuspendProcess:
    """Tests for suspend_process()."""

    def test_suspend_process_sends_sigstp(self) -> None:
        """suspend_process sends SIGTSTP to current process."""
        with patch("claude_code.cli.suspend.is_interactive", return_value=True), \
                patch("claude_code.cli.suspend.os.kill") as mock_kill, \
                patch("claude_code.cli.suspend.os.getpid", return_value=999):
            suspend_process()
        mock_kill.assert_called_once_with(999, signal.SIGTSTP)

    def test_suspend_process_noop_when_not_interactive(self) -> None:
        """suspend_process does nothing when not in interactive terminal."""
        with patch("claude_code.cli.suspend.is_interactive", return_value=False), \
                patch("claude_code.cli.suspend.os.kill") as mock_kill:
            suspend_process()
        mock_kill.assert_not_called()

    def test_suspend_process_noop_on_oserror(self) -> None:
        """suspend_process silently handles OSError."""
        with patch("claude_code.cli.suspend.is_interactive", return_value=True), \
                patch("claude_code.cli.suspend.os.kill", side_effect=OSError()):
            suspend_process()  # Should not raise


class TestSendToBackground:
    """Tests for send_to_background()."""

    def test_send_to_background_returns_zero_on_success(self) -> None:
        """send_to_background returns 0 on success."""
        with patch("claude_code.cli.suspend.is_interactive", return_value=True), \
                patch("claude_code.cli.suspend.os.getpid", return_value=999), \
                patch("claude_code.cli.suspend.os.getpgid", return_value=100), \
                patch("claude_code.cli.suspend.os.killpg"):
            result = send_to_background()
        assert result == 0

    def test_send_to_background_returns_minus_one_when_not_interactive(self) -> None:
        """send_to_background returns -1 when not interactive."""
        with patch("claude_code.cli.suspend.is_interactive", return_value=False):
            result = send_to_background()
        assert result == -1

    def test_send_to_background_returns_minus_one_on_oserror(self) -> None:
        """send_to_background returns -1 on OSError."""
        with patch("claude_code.cli.suspend.is_interactive", return_value=True), \
                patch("claude_code.cli.suspend.os.getpid", return_value=999), \
                patch("claude_code.cli.suspend.os.getpgid", side_effect=OSError()):
            result = send_to_background()
        assert result == -1


class TestGlobalFunctions:
    """Tests for global suspend management functions."""

    def test_get_suspend_manager_creates_instance(self) -> None:
        """get_suspend_manager returns a SuspendManager."""
        # Reset global state
        import claude_code.cli.suspend as suspend_mod

        suspend_mod._suspend_manager = None
        try:
            mgr = get_suspend_manager()
            assert isinstance(mgr, SuspendManager)
            # Calling again returns the same instance
            assert get_suspend_manager() is mgr
        finally:
            suspend_mod._suspend_manager = None

    def test_setup_suspend_creates_and_setups_manager(self) -> None:
        """setup_suspend creates and sets up a manager."""
        import claude_code.cli.suspend as suspend_mod

        suspend_mod._suspend_manager = None
        try:
            on_suspend = MagicMock()
            mgr = setup_suspend(on_suspend=on_suspend)
            assert isinstance(mgr, SuspendManager)
            assert mgr._on_suspend is on_suspend
            assert suspend_mod._suspend_manager is mgr
        finally:
            suspend_mod._suspend_manager = None

    def test_teardown_suspend_restores_manager(self) -> None:
        """teardown_suspend restores the global manager."""
        import claude_code.cli.suspend as suspend_mod

        mgr = SuspendManager()
        suspend_mod._suspend_manager = mgr
        try:
            with patch.object(mgr, "restore"):
                teardown_suspend()
            assert suspend_mod._suspend_manager is None
        finally:
            suspend_mod._suspend_manager = None

    def test_teardown_suspend_noop_when_none(self) -> None:
        """teardown_suspend is safe when manager is None."""
        import claude_code.cli.suspend as suspend_mod

        suspend_mod._suspend_manager = None
        teardown_suspend()  # Should not raise
