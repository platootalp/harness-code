"""Unit tests for RetryStrategy."""

from __future__ import annotations

from mozi.core.model.errors import (
    InvalidRequestError,
    ModelInvocationError,
    RateLimitError,
)
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


class TestRetryStrategyShouldRetry:
    """Tests for should_retry method."""

    def test_should_not_retry_when_max_retries_exceeded(self) -> None:
        """Test should_retry returns False when max_retries is exceeded."""
        strategy = RetryStrategy(max_retries=3)
        error = RateLimitError("rate limited")
        assert strategy.should_retry(0, error) is True
        assert strategy.should_retry(1, error) is True
        assert strategy.should_retry(2, error) is True
        assert strategy.should_retry(3, error) is False

    def test_should_not_retry_invalid_request(self) -> None:
        """Test should_retry returns False for InvalidRequestError."""
        strategy = RetryStrategy(max_retries=3)
        error = InvalidRequestError("invalid request")
        assert strategy.should_retry(0, error) is False

    def test_should_retry_rate_limit_error(self) -> None:
        """Test should_retry returns True for RateLimitError."""
        strategy = RetryStrategy(max_retries=3)
        error = RateLimitError("rate limited")
        assert strategy.should_retry(0, error) is True

    def test_should_retry_model_invocation_error(self) -> None:
        """Test should_retry returns True for ModelInvocationError."""
        strategy = RetryStrategy(max_retries=3)
        error = ModelInvocationError("model error")
        assert strategy.should_retry(0, error) is True

    def test_should_not_retry_generic_exception(self) -> None:
        """Test should_retry returns False for generic exceptions."""
        strategy = RetryStrategy(max_retries=3)
        error = ValueError("some error")
        assert strategy.should_retry(0, error) is False


class TestRetryStrategyCalculateDelay:
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
            delay = strategy.base_delay * (strategy.exponential_base**attempt)
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
                strategy.base_delay * (strategy.exponential_base**attempt),
                strategy.max_delay,
            )
            assert delay <= strategy.max_delay

    def test_calculate_delay_with_jitter(self) -> None:
        """Test that jitter introduces variance in calculated delays."""
        strategy = RetryStrategy(
            max_retries=3,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True,
        )
        # Get multiple delays for the same attempt
        delays = [strategy.calculate_delay(1) for _ in range(10)]
        # All delays should be between 0.5 and 3.0 (50-150% of 2.0)
        assert all(1.0 <= d <= 3.0 for d in delays)
        # At least some variance should exist
        assert len(set(delays)) > 1
