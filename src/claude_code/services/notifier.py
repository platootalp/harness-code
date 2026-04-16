"""Desktop notification service.

TypeScript equivalent: src/services/notifier.ts
"""

from __future__ import annotations

import logging
import os
import random
import subprocess
import sys
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class NotificationChannel(StrEnum):
    AUTO = "auto"
    ITERM2 = "iterm2"
    ITERM2_WITH_BELL = "iterm2_with_bell"
    KITTY = "kitty"
    GHOSTTY = "ghostty"
    TERMINAL_BELL = "terminal_bell"
    DISABLED = "notifications_disabled"


@dataclass
class NotificationOptions:
    """Options for a notification."""

    message: str
    title: str = "Claude Code"
    notification_type: str = "default"


class Notifier:
    """Desktop notification service.

    Supports multiple notification channels:
    - auto: Automatically detect the best available method
    - iterm2: iTerm2-specific notifications
    - kitty: Kitty terminal notifications
    - ghostty: Ghostty terminal notifications
    - terminal_bell: Terminal bell character
    - disabled: No notifications
    """

    def __init__(self, channel: NotificationChannel = NotificationChannel.AUTO) -> None:
        """Initialize notifier.

        Args:
            channel: The notification channel to use.
        """
        self.channel = channel

    async def send(self, options: NotificationOptions) -> str:
        """Send a notification.

        Args:
            options: Notification options.

        Returns:
            The notification method used.
        """
        if self.channel == NotificationChannel.AUTO:
            return await self._send_auto(options)
        elif self.channel == NotificationChannel.ITERM2:
            self._send_iterm2(options)
            return "iterm2"
        elif self.channel == NotificationChannel.ITERM2_WITH_BELL:
            self._send_iterm2(options)
            self._send_terminal_bell()
            return "iterm2_with_bell"
        elif self.channel == NotificationChannel.KITTY:
            self._send_kitty(options)
            return "kitty"
        elif self.channel == NotificationChannel.GHOSTTY:
            self._send_ghostty(options)
            return "ghostty"
        elif self.channel == NotificationChannel.TERMINAL_BELL:
            self._send_terminal_bell()
            return "terminal_bell"
        elif self.channel == NotificationChannel.DISABLED:
            return "disabled"
        else:
            return "none"

    async def _send_auto(self, options: NotificationOptions) -> str:
        """Auto-detect best notification method.

        Detects terminal type and uses appropriate notification method.

        Args:
            options: Notification options.

        Returns:
            The notification method used.
        """
        terminal = os.environ.get("TERM", "")

        # Detect Apple Terminal
        if terminal == "dumb":
            # Check for Apple Terminal via Apple_Terminal env
            if os.environ.get("TERM_PROGRAM") == "Apple_Terminal":
                if await self._is_apple_terminal_bell_disabled():
                    self._send_terminal_bell()
                    return "terminal_bell"
                return "no_method_available"
            return "no_method_available"

        # Detect iTerm2
        if os.environ.get("TERM_PROGRAM") == "iTerm.app":
            self._send_iterm2(options)
            return "iterm2"

        # Detect Kitty
        if terminal.startswith("xterm-kitty"):
            self._send_kitty(options)
            return "kitty"

        # Detect Ghostty
        if terminal.startswith("ghostty"):
            self._send_ghostty(options)
            return "ghostty"

        # Default: try terminal bell
        self._send_terminal_bell()
        return "terminal_bell"

    def _send_iterm2(self, options: NotificationOptions) -> None:
        """Send iTerm2 notification.

        Uses iTerm2's proprietary escape sequences for notifications.

        Args:
            options: Notification options.
        """
        try:
            title = options.title.replace('"', '\\"')
            message = options.message.replace('"', '\\"')
            notif_type = options.notification_type

            # iTerm2 notification escape sequence
            # See https://www.iterm2.com/documentation-notifications.html
            sequence = (
                f'\033]9;message={message}\007\033]9;{notif_type}\007'
                f'\033]1337;service={title}\007'
            )
            sys.stdout.write(sequence)
            sys.stdout.flush()
        except Exception as e:
            logger.error("Failed to send iTerm2 notification: %s", e)

    def _send_terminal_bell(self) -> None:
        """Send terminal bell character (\\a)."""
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception as e:
            logger.error("Failed to send terminal bell: %s", e)

    def _send_kitty(self, options: NotificationOptions) -> None:
        """Send Kitty notification.

        Uses Kitty's notification extension.

        Args:
            options: Notification options.
        """
        try:
            title = options.title.replace('"', '\\"')
            message = options.message.replace('"', '\\"')
            notif_id = random.randint(0, 9999)

            # Kitty notification escape sequence
            # See https://sw.kovidgoyal.net/kitty/shell-integration/
            sequence = f'\033]99;T:title={title}|id={notif_id}|msg={message}\a'
            sys.stdout.write(sequence)
            sys.stdout.flush()
        except Exception as e:
            logger.error("Failed to send Kitty notification: %s", e)

    def _send_ghostty(self, options: NotificationOptions) -> None:
        """Send Ghostty notification.

        Uses Ghostty's notification extension.

        Args:
            options: Notification options.
        """
        try:
            title = options.title.replace('"', '\\"')
            message = options.message.replace('"', '\\"')

            # Ghostty notification escape sequence
            sequence = f'\033]99;T:title={title}|body={message}\a'
            sys.stdout.write(sequence)
            sys.stdout.flush()
        except Exception as e:
            logger.error("Failed to send Ghostty notification: %s", e)

    async def _is_apple_terminal_bell_disabled(self) -> bool:
        """Check if Apple Terminal bell is disabled.

        Returns:
            True if bell is disabled, False otherwise.
        """
        try:
            result = subprocess.run(
                [
                    "defaults",
                    "export",
                    "com.apple.Terminal",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False

            # Parse plist output for bell settings
            # This is a simplified check - the full implementation
            # would parse the plist XML
            return "Bell" in result.stdout and "false" in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False


async def send_notification(
    message: str,
    title: str = "Claude Code",
    notification_type: str = "default",
) -> str:
    """Convenience function to send a notification.

    Args:
        message: The notification message.
        title: The notification title.
        notification_type: Type of notification.

    Returns:
        The notification method used.
    """
    notifier = Notifier()
    options = NotificationOptions(
        message=message,
        title=title,
        notification_type=notification_type,
    )
    return await notifier.send(options)
