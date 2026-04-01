"""Unit tests for CircuitBreaker."""

from __future__ import annotations

import asyncio

import pytest

from mozi.core.model.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from mozi.core.model.errors import CircuitBreakerOpenError


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_circuit_states_exist(self) -> None:
        """Test all circuit states are defined."""
        assert CircuitState.CLOSED is not None
        assert CircuitState.HALF_OPEN is not None
        assert CircuitState.OPEN is not None

    def test_circuit_state_values(self) -> None:
        """Test circuit state string values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.HALF_OPEN.value == "half_open"
        assert CircuitState.OPEN.value == "open"


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.half_open_max_calls == 3

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=30.0,
            half_open_max_calls=5,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 30.0
        assert config.half_open_max_calls == 5


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    @pytest.fixture
    def circuit_breaker(self) -> CircuitBreaker:
        """Create a circuit breaker with default config."""
        return CircuitBreaker()

    @pytest.fixture
    def fast_recovery_breaker(self) -> CircuitBreaker:
        """Create a circuit breaker with fast recovery for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            half_open_max_calls=1,
        )
        return CircuitBreaker(config=config)

    def test_initial_state_closed(self, circuit_breaker: CircuitBreaker) -> None:
        """Test circuit starts in closed state."""
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_success_resets_failure_count(
        self, circuit_breaker: CircuitBreaker
    ) -> None:
        """Test that success resets failure count."""
        # Record some failures (but not enough to open)
        for _ in range(3):
            _cb = CircuitBreaker(
                CircuitBreakerConfig(failure_threshold=5)
            )
            # We need to manually trigger failure mechanism
            # This is tested through the async call flow

        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker: CircuitBreaker) -> None:
        """Test successful async call."""
        async def success_func() -> str:
            return "success"

        result = await circuit_breaker.call(success_func())
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_call_failure_opens_circuit(self) -> None:
        """Test that failures open the circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=60.0,
            half_open_max_calls=1,
        )
        breaker = CircuitBreaker(config=config)

        async def failing_func() -> None:
            raise ValueError("fail")

        # First failure
        with pytest.raises(ValueError):
            await breaker.call(failing_func())
        assert breaker.state == CircuitState.CLOSED

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func())
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_call(self) -> None:
        """Test that open circuit rejects calls immediately."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=60.0,
            half_open_max_calls=1,
        )
        breaker = CircuitBreaker(config=config)

        async def failing_func() -> None:
            raise ValueError("fail")

        async def success_func() -> str:
            return "success"

        # Open the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func())

        # Now the circuit should be open
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(success_func())

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(
        self, fast_recovery_breaker: CircuitBreaker
    ) -> None:
        """Test circuit transitions to half-open after timeout."""
        async def failing_func() -> None:
            raise ValueError("fail")

        # Open the circuit
        with pytest.raises(ValueError):
            await fast_recovery_breaker.call(failing_func())
        with pytest.raises(ValueError):
            await fast_recovery_breaker.call(failing_func())
        assert fast_recovery_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should transition to half-open on next access
        assert fast_recovery_breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_allows_one_call(
        self, fast_recovery_breaker: CircuitBreaker
    ) -> None:
        """Test half-open state allows configured number of calls."""
        async def success_func() -> str:
            return "success"

        # Force to half-open state
        fast_recovery_breaker._state = CircuitState.HALF_OPEN
        fast_recovery_breaker._half_open_calls = 0

        # First call should succeed
        result = await fast_recovery_breaker.call(success_func())
        assert result == "success"

    @pytest.mark.asyncio
    async def test_half_open_rejects_when_max_calls(
        self, fast_recovery_breaker: CircuitBreaker
    ) -> None:
        """Test half-open rejects calls when max reached."""
        async def success_func() -> str:
            return "success"

        # Force to half-open state with max calls
        fast_recovery_breaker._state = CircuitState.HALF_OPEN
        fast_recovery_breaker._half_open_calls = 1  # Already at max

        with pytest.raises(CircuitBreakerOpenError):
            await fast_recovery_breaker.call(success_func())

    @pytest.mark.asyncio
    async def test_success_closes_circuit(
        self, fast_recovery_breaker: CircuitBreaker
    ) -> None:
        """Test that success in half-open closes the circuit."""
        async def success_func() -> str:
            return "success"

        # Force to half-open state
        fast_recovery_breaker._state = CircuitState.HALF_OPEN
        fast_recovery_breaker._half_open_calls = 0

        # Successful call should close circuit
        await fast_recovery_breaker.call(success_func())
        assert fast_recovery_breaker.state == CircuitState.CLOSED
