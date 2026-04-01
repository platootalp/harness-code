"""Retry strategy implementation.

Provides retry logic with exponential backoff for transient failures.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

from mozi.core.model.errors import (
    InvalidRequestError,
    ModelInvocationError,
    RateLimitError,
)

# Errors that are retryable
RETRYABLE_ERRORS = (RateLimitError, ModelInvocationError)


@dataclass
class RetryStrategy:
    """Retry strategy with exponential backoff.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Base for exponential calculation.
        jitter: Whether to add random jitter to delays.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Determine if a request should be retried.

        Args:
            attempt: Current attempt number (0-indexed).
            error: The exception that occurred.

        Returns:
            True if should retry, False otherwise.
        """
        if attempt >= self.max_retries:
            return False

        # Don't retry invalid requests
        if isinstance(error, InvalidRequestError):
            return False

        # Retry retryable errors
        return isinstance(error, RETRYABLE_ERRORS)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry.

        Args:
            attempt: Current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = self.base_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random
            delay *= 0.5 + random.random()  # 50-150% of calculated delay

        return delay


async def execute_with_retry(
    func: Coroutine[Any, Any, Any],
    strategy: RetryStrategy | None = None,
) -> Any:
    """Execute an async function with retry logic.

    Args:
        func: Async function to execute.
        strategy: Retry strategy to use. Uses default if None.

    Returns:
        Result of the function call.

    Raises:
        The last exception if all retries are exhausted.
    """
    if strategy is None:
        strategy = RetryStrategy()

    attempt = 0

    while True:
        try:
            return await func
        except Exception as e:
            if not strategy.should_retry(attempt, e):
                raise

            delay = strategy.calculate_delay(attempt)
            await asyncio.sleep(delay)
            attempt += 1
