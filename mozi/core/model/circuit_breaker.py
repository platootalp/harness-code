"""Circuit breaker implementation.

Provides fault tolerance by preventing cascading failures.
"""

from __future__ import annotations

import time
from collections.abc import Coroutine
from dataclasses import dataclass
from enum import Enum
from typing import Any

from mozi.core.model.errors import CircuitBreakerOpenError


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker.

    Attributes:
        failure_threshold: Number of failures before opening circuit.
        recovery_timeout: Seconds to wait before attempting recovery.
        half_open_max_calls: Max calls allowed in half-open state.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures.

    When failures exceed a threshold, the circuit "opens" and
    immediately fails requests without attempting the operation.
    After a recovery timeout, it allows a few test requests
    through in a "half-open" state.
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration.
        """
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        self._check_state_transition()
        return self._state

    def _check_state_transition(self) -> None:
        """Check if state should transition based on timeout."""
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self._config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

    def _on_failure(self) -> None:
        """Record a failure."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self._config.failure_threshold:
            self._state = CircuitState.OPEN

    def _on_success(self) -> None:
        """Record a success."""
        self._failure_count = 0
        self._half_open_calls = 0
        self._state = CircuitState.CLOSED

    async def call(self, func: Coroutine[Any, Any, Any]) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to execute.

        Returns:
            Result of the function.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
        """
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.time() - self._last_failure_time
                if elapsed < self._config.recovery_timeout:
                    raise CircuitBreakerOpenError()
            # Transition to half-open
            self._state = CircuitState.HALF_OPEN
            self._half_open_calls = 0

        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self._config.half_open_max_calls:
                raise CircuitBreakerOpenError()
            self._half_open_calls += 1

        try:
            result = await func
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
