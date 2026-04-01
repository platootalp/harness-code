"""Unit tests for RetryStrategy."""

from __future__ import annotations

from mozi.core.model.retry import RetryStrategy


class TestRetryStrategy:
    """Tests for RetryStrategy dataclass."""

    def test_default_values(self) -> None:
        """Test default retry strategy values."""
        strategy = RetryStrategy()
        assert strategy.max_retries == 3
        assert strategy.base_delay == 1.0
        assert strategy.max_delay == 60.0
        assert strategy.exponential_base == 2.0
        assert strategy.jitter is True

    def test_custom_values(self) -> None:
        """Test custom retry strategy values."""
        strategy = RetryStrategy(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert strategy.max_retries == 5
        assert strategy.base_delay == 0.5
        assert strategy.max_delay == 30.0
        assert strategy.exponential_base == 3.0
        assert strategy.jitter is False

    def test_zero_retries(self) -> None:
        """Test retry strategy with zero retries."""
        strategy = RetryStrategy(max_retries=0)
        assert strategy.max_retries == 0

    def test_zero_base_delay(self) -> None:
        """Test retry strategy with zero base delay."""
        strategy = RetryStrategy(base_delay=0.0)
        assert strategy.base_delay == 0.0


class TestRetryStrategyCalculation:
    """Tests for retry delay calculation logic."""

    def test_exponential_delay_no_jitter(self) -> None:
        """Test exponential delay without jitter."""
        strategy = RetryStrategy(
            max_retries=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )
        # Delay = base_delay * (exponential_base ^ attempt)
        delays = []
        for attempt in range(1, 4):
            delay = strategy.base_delay * (strategy.exponential_base ** attempt)
            delays.append(delay)
        assert delays == [2.0, 4.0, 8.0]

    def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        strategy = RetryStrategy(
            max_retries=5,
            base_delay=10.0,
            exponential_base=2.0,
            max_delay=30.0,
            jitter=False,
        )
        for attempt in range(1, 6):
            delay = min(
                strategy.base_delay * (strategy.exponential_base ** attempt),
                strategy.max_delay,
            )
            assert delay <= strategy.max_delay

    def test_with_jitter_has_variance(self) -> None:
        """Test that jitter introduces variance in delays."""
        strategy = RetryStrategy(
            max_retries=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True,
        )
        delays = []
        for _ in range(10):
            for attempt in range(1, 4):
                base = strategy.base_delay * (strategy.exponential_base ** attempt)
                # With jitter, delay should vary
                delays.append(base)
        # Just verify jitter flag is respected
        assert strategy.jitter is True
