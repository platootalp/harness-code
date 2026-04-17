"""
Tests for bridge/recovery.py - Bridge error recovery with reconnection logic.
"""

from __future__ import annotations

import time
from typing import Any

import pytest


class TestBridgeRecoveryExceptions:
    """Tests for recovery exception classes."""

    def test_bridge_recovery_error(self) -> None:
        """BridgeRecoveryError can be raised."""
        from claude_code.bridge.recovery import BridgeRecoveryError

        with pytest.raises(BridgeRecoveryError):
            raise BridgeRecoveryError("test error")

    def test_bridge_recovery_exhausted(self) -> None:
        """BridgeRecoveryExhausted is a subclass of BridgeRecoveryError."""
        from claude_code.bridge.recovery import (
            BridgeRecoveryError,
            BridgeRecoveryExhausted,
        )

        assert issubclass(BridgeRecoveryExhausted, BridgeRecoveryError)

        with pytest.raises(BridgeRecoveryExhausted):
            raise BridgeRecoveryExhausted("attempts exhausted")

    def test_bridge_recovery_timeout(self) -> None:
        """BridgeRecoveryTimeout is a subclass of BridgeRecoveryError."""
        from claude_code.bridge.recovery import (
            BridgeRecoveryError,
            BridgeRecoveryTimeout,
        )

        assert issubclass(BridgeRecoveryTimeout, BridgeRecoveryError)

        with pytest.raises(BridgeRecoveryTimeout):
            raise BridgeRecoveryTimeout("timeout")


class TestRecoveryStats:
    """Tests for RecoveryStats dataclass."""

    def test_default_values(self) -> None:
        """RecoveryStats has correct default values."""
        from claude_code.bridge.recovery import RecoveryStats

        stats = RecoveryStats()
        assert stats.consecutive_errors == 0
        assert stats.first_error_time is None
        assert stats.reconnect_attempts == 0
        assert stats.last_error_time is None
        assert stats.total_errors == 0
        assert stats.total_reconnects == 0

    def test_to_dict(self) -> None:
        """to_dict returns correct representation."""
        from claude_code.bridge.recovery import RecoveryStats

        stats = RecoveryStats(consecutive_errors=3, total_errors=5)
        d = stats.to_dict()
        assert d["consecutive_errors"] == 3
        assert d["total_errors"] == 5
        assert d["first_error_time"] is None


class TestBridgeRecoveryInit:
    """Tests for BridgeRecovery initialization."""

    def test_default_init(self) -> None:
        """BridgeRecovery initializes with correct defaults."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        assert recovery.max_reconnect_attempts == 10
        assert recovery.is_in_error_state is False
        assert recovery.stats.consecutive_errors == 0

    def test_custom_init(self) -> None:
        """BridgeRecovery accepts custom parameters."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery(
            max_reconnect_attempts=5,
            initial_delay_ms=1000,
            max_delay_ms=30000,
            give_up_ms=300000,
        )
        assert recovery.max_reconnect_attempts == 5


class TestBridgeRecoveryBackoff:
    """Tests for backoff calculation."""

    def test_calculate_backoff_increases(self) -> None:
        """Backoff increases with consecutive errors."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()

        delay1 = recovery.calculate_backoff(0)
        delay2 = recovery.calculate_backoff(1)
        delay3 = recovery.calculate_backoff(2)

        # Exponential increase (with jitter)
        assert delay2 > delay1
        assert delay3 > delay2

    def test_calculate_backoff_max_cap(self) -> None:
        """Backoff is capped at max_delay_ms."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery(max_delay_ms=5000)

        # Large attempt number should be capped at 5000ms base
        # With ±25% jitter, max delay = 5000 * 1.25 = 6250ms = 6.25s
        delay = recovery.calculate_backoff(attempt=100)
        assert delay <= 6.5  # Allow for ±25% jitter

    def test_calculate_backoff_uses_consecutive_errors(self) -> None:
        """calculate_backoff uses consecutive_errors when attempt not specified."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()
        recovery.record_error()
        recovery.record_error()

        delay = recovery.calculate_backoff()
        # Should be using attempt=2 (3 errors - 1)
        assert delay > 0


class TestBridgeRecoveryShouldGiveUp:
    """Tests for should_give_up logic."""

    def test_no_give_up_initially(self) -> None:
        """should_give_up returns False initially."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        assert recovery.should_give_up() is False

    def test_give_up_after_max_attempts(self) -> None:
        """should_give_up returns True after max reconnect attempts."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery(max_reconnect_attempts=3)
        recovery._stats.consecutive_errors = 3
        recovery._stats.first_error_time = time.time()  # must be set for give_up check

        assert recovery.should_give_up() is True

    def test_give_up_after_time_budget(self) -> None:
        """should_give_up returns True after time budget exceeded."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery(give_up_ms=1000)
        recovery._stats.first_error_time = time.time() - 2  # 2 seconds ago

        assert recovery.should_give_up() is True


class TestBridgeRecoverySleepDetection:
    """Tests for system sleep detection."""

    def test_no_reset_without_gap(self) -> None:
        """should_reset_on_sleep returns False without large time gap."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()

        # Just recorded error, no gap
        assert recovery.should_reset_on_sleep() is False

    def test_reset_after_long_gap(self) -> None:
        """should_reset_on_sleep returns True after long gap."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery(max_delay_ms=1000)
        recovery._last_poll_error_time = time.time() - 5  # 5 seconds ago
        recovery._stats.first_error_time = time.time() - 5

        # Gap of 5s > 2 * max_delay_ms (2s)
        assert recovery.should_reset_on_sleep() is True


class TestBridgeRecoveryRecordError:
    """Tests for record_error."""

    def test_record_error_increments_counters(self) -> None:
        """record_error increments error counters."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()

        assert recovery.stats.consecutive_errors == 1
        assert recovery.stats.total_errors == 1
        assert recovery.is_in_error_state is True

    def test_record_error_multiple(self) -> None:
        """Multiple errors accumulate correctly."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()
        recovery.record_error()
        recovery.record_error()

        assert recovery.stats.consecutive_errors == 3
        assert recovery.stats.total_errors == 3

    def test_record_error_returns_delay(self) -> None:
        """record_error returns calculated backoff delay."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        delay = recovery.record_error()

        assert isinstance(delay, float)
        assert delay > 0


class TestBridgeRecoveryRecordSuccess:
    """Tests for record_success."""

    def test_record_success_resets_errors(self) -> None:
        """record_success resets consecutive error count."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()
        recovery.record_error()
        recovery.record_success()

        assert recovery.stats.consecutive_errors == 0
        assert recovery.stats.first_error_time is None

    def test_record_success_increments_reconnects(self) -> None:
        """record_success increments reconnect counters."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_success()

        assert recovery.stats.total_reconnects == 1
        assert recovery.stats.reconnect_attempts == 1


class TestBridgeRecoveryRecordReconnectAttempt:
    """Tests for record_reconnect_attempt."""

    def test_increments_attempt_counter(self) -> None:
        """record_reconnect_attempt increments attempt counter."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_reconnect_attempt()
        recovery.record_reconnect_attempt()

        assert recovery.stats.reconnect_attempts == 2


class TestBridgeRecoveryReset:
    """Tests for reset."""

    def test_full_reset(self) -> None:
        """reset clears all state."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()
        recovery.record_reconnect_attempt()
        recovery.reset()

        assert recovery.stats.consecutive_errors == 0
        assert recovery.stats.total_errors == 0
        assert recovery.stats.reconnect_attempts == 0
        assert recovery.is_in_error_state is False


class TestBridgeRecoveryGetBackoffInfo:
    """Tests for get_backoff_info."""

    def test_backoff_info_structure(self) -> None:
        """get_backoff_info returns correct structure."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        recovery.record_error()

        info = recovery.get_backoff_info()
        assert "consecutive_errors" in info
        assert "elapsed_ms" in info
        assert "current_backoff_ms" in info
        assert "max_backoff_ms" in info
        assert "give_up_ms" in info
        assert "should_give_up" in info

    def test_backoff_info_values(self) -> None:
        """get_backoff_info returns correct values."""
        from claude_code.bridge.recovery import BridgeRecovery

        recovery = BridgeRecovery()
        info = recovery.get_backoff_info()

        assert info["consecutive_errors"] == 0
        assert info["should_give_up"] is False


class TestConstants:
    """Tests for module constants."""

    def test_poll_error_constants(self) -> None:
        """Poll error constants have expected values."""
        from claude_code.bridge.recovery import (
            POLL_ERROR_GIVE_UP_MS,
            POLL_ERROR_INITIAL_DELAY_MS,
            POLL_ERROR_MAX_DELAY_MS,
        )

        assert POLL_ERROR_INITIAL_DELAY_MS == 2000
        assert POLL_ERROR_MAX_DELAY_MS == 60000
        assert POLL_ERROR_GIVE_UP_MS == 15 * 60 * 1000

    def test_reconnect_defaults(self) -> None:
        """Reconnect defaults have expected values."""
        from claude_code.bridge.recovery import (
            DEFAULT_BASE_RECONNECT_DELAY,
            DEFAULT_MAX_RECONNECT_DELAY,
            DEFAULT_RECONNECT_GIVE_UP_SECONDS,
        )

        assert DEFAULT_BASE_RECONNECT_DELAY == 1.0
        assert DEFAULT_MAX_RECONNECT_DELAY == 30.0
        assert DEFAULT_RECONNECT_GIVE_UP_SECONDS == 600.0
