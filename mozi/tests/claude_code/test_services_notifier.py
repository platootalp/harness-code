"""Tests for services/notifier.py - Notifier."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from claude_code.services.notifier import (
    NotificationChannel,
    NotificationOptions,
    Notifier,
    send_notification,
)


class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_all_channels(self) -> None:
        """Test all notification channels are defined."""
        assert NotificationChannel.AUTO == "auto"
        assert NotificationChannel.ITERM2 == "iterm2"
        assert NotificationChannel.ITERM2_WITH_BELL == "iterm2_with_bell"
        assert NotificationChannel.KITTY == "kitty"
        assert NotificationChannel.GHOSTTY == "ghostty"
        assert NotificationChannel.TERMINAL_BELL == "terminal_bell"
        assert NotificationChannel.DISABLED == "notifications_disabled"


class TestNotificationOptions:
    """Tests for NotificationOptions dataclass."""

    def test_default_values(self) -> None:
        """Test default notification options."""
        opts = NotificationOptions(message="Hello")
        assert opts.message == "Hello"
        assert opts.title == "Claude Code"
        assert opts.notification_type == "default"

    def test_full_options(self) -> None:
        """Test notification options with all fields."""
        opts = NotificationOptions(
            message="Task complete",
            title="Custom Title",
            notification_type="success",
        )
        assert opts.message == "Task complete"
        assert opts.title == "Custom Title"
        assert opts.notification_type == "success"


class TestNotifierInit:
    """Tests for Notifier initialization."""

    def test_default_channel(self) -> None:
        """Test default channel is AUTO."""
        notifier = Notifier()
        assert notifier.channel == NotificationChannel.AUTO

    def test_custom_channel(self) -> None:
        """Test setting custom channel."""
        notifier = Notifier(channel=NotificationChannel.ITERM2)
        assert notifier.channel == NotificationChannel.ITERM2


class TestNotifierSend:
    """Tests for Notifier.send method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.options = NotificationOptions(message="Test", title="Test Title")

    @pytest.mark.asyncio
    async def test_send_disabled(self) -> None:
        """Test sending when disabled returns 'disabled'."""
        notifier = Notifier(channel=NotificationChannel.DISABLED)
        result = await notifier.send(self.options)
        assert result == "disabled"

    @pytest.mark.asyncio
    async def test_send_iterm2(self) -> None:
        """Test sending via iTerm2."""
        notifier = Notifier(channel=NotificationChannel.ITERM2)
        result = await notifier.send(self.options)
        assert result == "iterm2"

    @pytest.mark.asyncio
    async def test_send_iterm2_with_bell(self) -> None:
        """Test sending via iTerm2 with bell."""
        notifier = Notifier(channel=NotificationChannel.ITERM2_WITH_BELL)
        result = await notifier.send(self.options)
        assert result == "iterm2_with_bell"

    @pytest.mark.asyncio
    async def test_send_kitty(self) -> None:
        """Test sending via Kitty."""
        notifier = Notifier(channel=NotificationChannel.KITTY)
        result = await notifier.send(self.options)
        assert result == "kitty"

    @pytest.mark.asyncio
    async def test_send_ghostty(self) -> None:
        """Test sending via Ghostty."""
        notifier = Notifier(channel=NotificationChannel.GHOSTTY)
        result = await notifier.send(self.options)
        assert result == "ghostty"

    @pytest.mark.asyncio
    async def test_send_terminal_bell(self) -> None:
        """Test sending via terminal bell."""
        notifier = Notifier(channel=NotificationChannel.TERMINAL_BELL)
        result = await notifier.send(self.options)
        assert result == "terminal_bell"

    @pytest.mark.asyncio
    async def test_unknown_channel(self) -> None:
        """Test unknown channel returns 'none'."""
        notifier = Notifier()  # AUTO
        # Override to test unknown path (won't happen with StrEnum)
        # Just verify AUTO path returns something
        result = await notifier._send_auto(self.options)
        assert result in ("terminal_bell", "no_method_available", "iterm2", "kitty", "ghostty")


class TestNotifierSendIterm2:
    """Tests for iTerm2 notification sending."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.options = NotificationOptions(
            message="Hello World",
            title="Test",
            notification_type="info",
        )

    def test_send_iterm2_escape_sequence(self) -> None:
        """Test iTerm2 sends proper escape sequences."""
        notifier = Notifier(channel=NotificationChannel.ITERM2)
        written = ""
        def capture_write(s: str) -> None:
            nonlocal written
            written += s
        with patch("sys.stdout.write", side_effect=capture_write):
            with patch("sys.stdout.flush"):
                notifier._send_iterm2(self.options)
                # Verify escape sequence contains message and escape sequences
                assert "Hello World" in written
                assert "\x1b]" in written

    def test_send_iterm2_handles_quotes(self) -> None:
        """Test iTerm2 properly escapes quotes."""
        options = NotificationOptions(message='Say "Hello"', title='Title "Test"')
        notifier = Notifier(channel=NotificationChannel.ITERM2)
        # Should not raise
        notifier._send_iterm2(options)

    def test_send_iterm2_exception_handled(self) -> None:
        """Test iTerm2 send handles exceptions gracefully."""
        notifier = Notifier(channel=NotificationChannel.ITERM2)
        with patch("sys.stdout.write", side_effect=IOError("broken")):
            # Should not raise
            notifier._send_iterm2(self.options)


class TestNotifierSendTerminalBell:
    """Tests for terminal bell sending."""

    def test_send_terminal_bell_writes_bell(self) -> None:
        """Test terminal bell writes \\a character."""
        notifier = Notifier(channel=NotificationChannel.TERMINAL_BELL)
        with patch("sys.stdout.write") as mock_write:
            notifier._send_terminal_bell()
            mock_write.assert_called_once_with("\a")

    def test_send_terminal_bell_exception_handled(self) -> None:
        """Test terminal bell handles exceptions gracefully."""
        notifier = Notifier(channel=NotificationChannel.TERMINAL_BELL)
        with patch("sys.stdout.write", side_effect=IOError("broken")):
            # Should not raise
            notifier._send_terminal_bell()


class TestNotifierSendKitty:
    """Tests for Kitty notification sending."""

    def test_send_kitty_escape_sequence(self) -> None:
        """Test Kitty sends proper escape sequence."""
        options = NotificationOptions(message="Kitty msg", title="Kitty Title")
        notifier = Notifier(channel=NotificationChannel.KITTY)
        written = ""
        def capture_write(s: str) -> None:
            nonlocal written
            written += s
        with patch("sys.stdout.write", side_effect=capture_write):
            with patch("sys.stdout.flush"):
                notifier._send_kitty(options)
                # The escape character is \x1b (same as \033)
                assert "\x1b]99;" in written

    def test_send_kitty_exception_handled(self) -> None:
        """Test Kitty send handles exceptions gracefully."""
        options = NotificationOptions(message="error", title="test")
        notifier = Notifier(channel=NotificationChannel.KITTY)
        with patch("sys.stdout.write", side_effect=IOError("broken")):
            notifier._send_kitty(options)


class TestNotifierSendGhostty:
    """Tests for Ghostty notification sending."""

    def test_send_ghostty_escape_sequence(self) -> None:
        """Test Ghostty sends proper escape sequence."""
        options = NotificationOptions(message="Ghostty msg", title="Ghostty Title")
        notifier = Notifier(channel=NotificationChannel.GHOSTTY)
        written = ""
        def capture_write(s: str) -> None:
            nonlocal written
            written += s
        with patch("sys.stdout.write", side_effect=capture_write):
            with patch("sys.stdout.flush"):
                notifier._send_ghostty(options)
                # The escape character is \x1b (same as \033)
                assert "\x1b]99;" in written

    def test_send_ghostty_exception_handled(self) -> None:
        """Test Ghostty send handles exceptions gracefully."""
        options = NotificationOptions(message="error", title="test")
        notifier = Notifier(channel=NotificationChannel.GHOSTTY)
        with patch("sys.stdout.write", side_effect=IOError("broken")):
            notifier._send_ghostty(options)


class TestNotifierAuto:
    """Tests for auto-detection logic."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.options = NotificationOptions(message="auto test")

    @pytest.mark.asyncio
    async def test_auto_detects_iterm2(self) -> None:
        """Test auto-detection finds iTerm2."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch.dict("os.environ", {"TERM_PROGRAM": "iTerm.app"}):
            with patch.object(notifier, "_send_iterm2"):
                result = await notifier._send_auto(self.options)
                assert result == "iterm2"

    @pytest.mark.asyncio
    async def test_auto_detects_kitty(self) -> None:
        """Test auto-detection finds Kitty."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch.dict("os.environ", {"TERM": "xterm-kitty", "TERM_PROGRAM": ""}):
            with patch.object(notifier, "_send_kitty"):
                result = await notifier._send_auto(self.options)
                assert result == "kitty"

    @pytest.mark.asyncio
    async def test_auto_detects_ghostty(self) -> None:
        """Test auto-detection finds Ghostty."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch.dict("os.environ", {"TERM": "ghostty", "TERM_PROGRAM": ""}):
            with patch.object(notifier, "_send_ghostty"):
                result = await notifier._send_auto(self.options)
                assert result == "ghostty"

    @pytest.mark.asyncio
    async def test_auto_falls_back_to_terminal_bell(self) -> None:
        """Test auto-detection falls back to terminal bell."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch.dict("os.environ", {"TERM": "xterm-256color", "TERM_PROGRAM": ""}):
            with patch.object(notifier, "_send_terminal_bell"):
                result = await notifier._send_auto(self.options)
                assert result == "terminal_bell"

    @pytest.mark.asyncio
    async def test_auto_dumb_terminal(self) -> None:
        """Test auto-detection with dumb terminal."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch.dict("os.environ", {"TERM": "dumb", "TERM_PROGRAM": ""}):
            with patch.object(notifier, "_send_terminal_bell"):
                with patch.object(notifier, "_is_apple_terminal_bell_disabled", return_value=False):
                    result = await notifier._send_auto(self.options)
                    # Should check Apple Terminal and return no_method_available
                    assert result in ("terminal_bell", "no_method_available")


class TestNotifierAppleTerminal:
    """Tests for Apple Terminal detection."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.options = NotificationOptions(message="apple test")

    @pytest.mark.asyncio
    async def test_is_apple_terminal_bell_disabled_false(self) -> None:
        """Test bell disabled check when Bell is not false."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="SomeProperty=true")
            result = await notifier._is_apple_terminal_bell_disabled()
            assert result is False

    @pytest.mark.asyncio
    async def test_is_apple_terminal_bell_disabled_true(self) -> None:
        """Test bell disabled check when Bell is false."""
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Bell=false")
            result = await notifier._is_apple_terminal_bell_disabled()
            assert result is True

    @pytest.mark.asyncio
    async def test_is_apple_terminal_bell_disabled_timeout(self) -> None:
        """Test bell disabled check handles timeout."""
        import subprocess
        notifier = Notifier(channel=NotificationChannel.AUTO)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            result = await notifier._is_apple_terminal_bell_disabled()
            assert result is False


class TestSendNotificationFunction:
    """Tests for send_notification convenience function."""

    @pytest.mark.asyncio
    async def test_send_notification_default(self) -> None:
        """Test convenience function with defaults."""
        with patch.object(Notifier, "send", return_value="terminal_bell") as mock:
            result = await send_notification("Hello")
            assert result == "terminal_bell"
            mock.assert_called_once()
            opts = mock.call_args[0][0]
            assert opts.message == "Hello"
            assert opts.title == "Claude Code"
            assert opts.notification_type == "default"

    @pytest.mark.asyncio
    async def test_send_notification_custom(self) -> None:
        """Test convenience function with custom values."""
        with patch.object(Notifier, "send", return_value="iterm2") as mock:
            result = await send_notification("Custom", title="My Title", notification_type="success")
            assert result == "iterm2"
            mock.assert_called_once()
