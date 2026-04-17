"""Bridge error recovery with reconnection logic.

Implements exponential backoff with jitter for poll/work errors,
and provides a structured recovery manager for the bridge lifecycle.

TypeScript equivalent: startWorkPollLoop in src/bridge/replBridge.ts
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Poll error recovery: exponential backoff constants
POLL_ERROR_INITIAL_DELAY_MS = 2000  # 2 seconds
POLL_ERROR_MAX_DELAY_MS = 60000  # 60 seconds (1 minute)
POLL_ERROR_GIVE_UP_MS = 15 * 60 * 1000  # 15 minutes

# Transport reconnection defaults
DEFAULT_BASE_RECONNECT_DELAY = 1.0  # seconds
DEFAULT_MAX_RECONNECT_DELAY = 30.0  # seconds
DEFAULT_RECONNECT_GIVE_UP_SECONDS = 600.0  # 10 minutes


# =============================================================================
# Exceptions
# =============================================================================


class BridgeRecoveryError(Exception):
    """Base exception for bridge recovery errors."""

    pass


class BridgeRecoveryExhausted(BridgeRecoveryError):
    """Raised when recovery attempts have been exhausted."""

    pass


class BridgeRecoveryTimeout(BridgeRecoveryError):
    """Raised when the recovery time budget has been exceeded."""

    pass


# =============================================================================
# Recovery Statistics
# =============================================================================


@dataclass
class RecoveryStats:
    """Statistics about recovery attempts.

    Tracks consecutive errors, timing, and reconnection state
    for the bridge error recovery system.

    Attributes:
        consecutive_errors: Number of consecutive poll errors.
        first_error_time: Unix timestamp when the first error occurred.
        reconnect_attempts: Number of reconnect attempts made.
        last_error_time: Unix timestamp of the most recent error.
        total_errors: Total number of errors encountered.
        total_reconnects: Total number of successful reconnects.
    """

    consecutive_errors: int = 0
    first_error_time: float | None = None
    reconnect_attempts: int = 0
    last_error_time: float | None = None
    total_errors: int = 0
    total_reconnects: int = 0

    def to_dict(self) -> dict[str, int | float | None]:
        """Return stats as a dictionary."""
        return {
            "consecutive_errors": self.consecutive_errors,
            "first_error_time": self.first_error_time,
            "reconnect_attempts": self.reconnect_attempts,
            "last_error_time": self.last_error_time,
            "total_errors": self.total_errors,
            "total_reconnects": self.total_reconnects,
        }


# =============================================================================
# Bridge Recovery
# =============================================================================


class BridgeRecovery:
    """Handles bridge reconnection with exponential backoff.

    Manages the error recovery lifecycle for bridge connections:
    - Tracks consecutive errors with exponential backoff
    - Detects system sleep/wake cycles (long gaps reset budget)
    - Respects a give-up timeout to prevent infinite retry
    - Resets on successful operations

    TypeScript equivalent: Error tracking in startWorkPollLoop in replBridge.ts

    Attributes:
        max_reconnect_attempts: Maximum number of reconnect attempts (per cycle).
        initial_delay_ms: Initial backoff delay in milliseconds.
        max_delay_ms: Maximum backoff delay in milliseconds.
        give_up_ms: Time budget in milliseconds before giving up.
    """

    def __init__(
        self,
        max_reconnect_attempts: int = 10,
        initial_delay_ms: float = POLL_ERROR_INITIAL_DELAY_MS,
        max_delay_ms: float = POLL_ERROR_MAX_DELAY_MS,
        give_up_ms: float = POLL_ERROR_GIVE_UP_MS,
    ) -> None:
        """Initialize the recovery manager.

        Args:
            max_reconnect_attempts: Maximum reconnect attempts before giving up.
            initial_delay_ms: Initial backoff delay in milliseconds.
            max_delay_ms: Maximum backoff delay in milliseconds.
            give_up_ms: Time budget in milliseconds before giving up on recovery.
        """
        self.max_reconnect_attempts = max_reconnect_attempts
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.give_up_ms = give_up_ms

        # Internal state
        self._stats = RecoveryStats()
        self._last_poll_error_time: float | None = None
        self._reset_time: float | None = None

    @property
    def stats(self) -> RecoveryStats:
        """Get current recovery statistics."""
        return self._stats

    @property
    def is_in_error_state(self) -> bool:
        """Whether we are currently in an error state (consecutive errors > 0)."""
        return self._stats.consecutive_errors > 0

    def calculate_backoff(self, attempt: int | None = None) -> float:
        """Calculate delay for a given attempt with jitter.

        Uses exponential backoff: delay = min(initial * 2^attempt, max) * (1 + jitter)
        where jitter is ±25% of the base delay.

        Args:
            attempt: The attempt number (0-indexed). If None, uses
                consecutive_errors count.

        Returns:
            The delay in seconds.
        """
        if attempt is None:
            attempt = self._stats.consecutive_errors - 1

        # Exponential base: 2s, 4s, 8s, 16s, 32s, 60s (capped)
        base_delay = min(
            self.initial_delay_ms * (2**attempt),
            self.max_delay_ms,
        )

        # Add ±25% jitter
        jitter_range = base_delay * 0.25
        jitter = jitter_range * (2 * random.random() - 1)
        delay_ms = base_delay + jitter

        # Clamp to positive
        delay_ms = max(0, delay_ms)

        return float(delay_ms / 1000.0)  # Convert to seconds

    def should_give_up(self, elapsed_ms: float | None = None) -> bool:
        """Check if recovery should give up.

        Args:
            elapsed_ms: Elapsed time since first error in milliseconds.
                If None, computed from first_error_time.

        Returns:
            True if recovery should give up.
        """
        if self._stats.first_error_time is None:
            return False

        if elapsed_ms is None:
            elapsed_ms = (time.time() - self._stats.first_error_time) * 1000

        if elapsed_ms >= self.give_up_ms:
            logger.warning(
                "[bridge:recovery] Recovery time budget exceeded: "
                "%.0fms > %.0fms (limit)",
                elapsed_ms,
                self.give_up_ms,
            )
            return True

        if self._stats.consecutive_errors >= self.max_reconnect_attempts:
            logger.warning(
                "[bridge:recovery] Recovery attempt limit reached: "
                "%d >= %d",
                self._stats.consecutive_errors,
                self.max_reconnect_attempts,
            )
            return True

        return False

    def should_reset_on_sleep(self, current_time: float | None = None) -> bool:
        """Check if error tracking should be reset due to system sleep.

        If the gap since the last error exceeds 2x the max backoff delay,
        the machine likely slept. Reset the error budget.

        Args:
            current_time: Current timestamp. Defaults to time.time().

        Returns:
            True if the error state should be reset.
        """
        if current_time is None:
            current_time = time.time()

        if (
            self._last_poll_error_time is not None
            and self._stats.first_error_time is not None
        ):
            gap = current_time - self._last_poll_error_time
            threshold_ms = self.max_delay_ms * 2
            if gap * 1000 > threshold_ms:
                logger.debug(
                    "[bridge:recovery] Detected system sleep "
                    "(%.0fs gap), resetting error budget",
                    gap,
                )
                return True

        return False

    def record_error(self, timestamp: float | None = None) -> float:
        """Record an error for backoff tracking.

        Updates consecutive error count and timestamps.

        Args:
            timestamp: Error timestamp. Defaults to time.time().

        Returns:
            The calculated backoff delay in seconds.
        """
        if timestamp is None:
            timestamp = time.time()

        self._last_poll_error_time = timestamp
        self._stats.total_errors += 1
        self._stats.consecutive_errors += 1
        self._stats.last_error_time = timestamp

        if self._stats.first_error_time is None:
            self._stats.first_error_time = timestamp
            self._reset_time = timestamp

        # Check for sleep detection
        if self.should_reset_on_sleep(timestamp):
            self._stats.consecutive_errors = 0
            self._stats.first_error_time = timestamp

        delay = self.calculate_backoff()
        logger.debug(
            "[bridge:recovery] Recorded error #%d, backoff=%.0fms",
            self._stats.consecutive_errors,
            delay * 1000,
        )
        return delay

    def record_success(self) -> None:
        """Reset error tracking after a successful operation.

        Called when a poll succeeds or a reconnect succeeds.
        """
        if self._stats.consecutive_errors > 0:
            logger.debug(
                "[bridge:recovery] Recovered after %d consecutive error(s)",
                self._stats.consecutive_errors,
            )
        self._stats.consecutive_errors = 0
        self._stats.first_error_time = None
        self._stats.reconnect_attempts += 1
        self._stats.total_reconnects += 1

    def record_reconnect_attempt(self) -> None:
        """Record a reconnect attempt (increments attempt counter)."""
        self._stats.reconnect_attempts += 1

    def reset(self) -> None:
        """Fully reset all recovery state."""
        self._stats = RecoveryStats()
        self._last_poll_error_time = None
        self._reset_time = None
        logger.debug("[bridge:recovery] Full reset performed")

    def get_backoff_info(self) -> dict[str, int | float]:
        """Get detailed backoff information for logging.

        Returns:
            A dict with backoff state information.
        """
        elapsed_ms: float | None = None
        if self._stats.first_error_time is not None:
            elapsed_ms = (time.time() - self._stats.first_error_time) * 1000

        return {
            "consecutive_errors": self._stats.consecutive_errors,
            "elapsed_ms": elapsed_ms or 0,
            "current_backoff_ms": self.calculate_backoff() * 1000,
            "max_backoff_ms": self.max_delay_ms,
            "give_up_ms": self.give_up_ms,
            "should_give_up": self.should_give_up(elapsed_ms),
        }
