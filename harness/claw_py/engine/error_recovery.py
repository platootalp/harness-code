"""
Error recovery and retry logic for the Claude Code engine.

This module implements exponential backoff retry with jitter for API operations,
including special handling for rate limits, 529 overload errors, and model fallback.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from ..services.api.errors import APIError

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_RETRIES = 10
BASE_DELAY_MS = 500
MAX_DELAY_MS = 32000
FLOOR_OUTPUT_TOKENS = 3000
MAX_529_RETRIES = 3

# Fast mode fallback constants
DEFAULT_FAST_MODE_FALLBACK_HOLD_MS = 30 * 60 * 1000  # 30 minutes
SHORT_RETRY_THRESHOLD_MS = 20 * 1000  # 20 seconds
MIN_COOLDOWN_MS = 10 * 60 * 1000  # 10 minutes

# Persistent retry constants
PERSISTENT_MAX_BACKOFF_MS = 5 * 60 * 1000  # 5 minutes
PERSISTENT_RESET_CAP_MS = 6 * 60 * 60 * 1000  # 6 hours
HEARTBEAT_INTERVAL_MS = 30_000  # 30 seconds


# =============================================================================
# Error Classes
# =============================================================================


class CannotRetryError(Exception):
    """Raised when an operation cannot be retried.

    Attributes:
        original_error: The original exception that caused the failure.
        retry_context: Context about the retry attempt.
    """

    def __init__(
        self,
        original_error: Exception,
        retry_context: RetryContext,
    ) -> None:
        message = str(original_error) if original_error else "Unknown error"
        super().__init__(message)
        self.name = "CannotRetryError"
        self.original_error = original_error
        self.retry_context = retry_context


class FallbackTriggeredError(Exception):
    """Raised when a model fallback is triggered due to repeated errors.

    Attributes:
        original_model: The model that failed.
        fallback_model: The model to fall back to.
    """

    def __init__(
        self,
        original_model: str,
        fallback_model: str,
    ) -> None:
        super().__init__(f"Model fallback triggered: {original_model} -> {fallback_model}")
        self.name = "FallbackTriggeredError"
        self.original_model = original_model
        self.fallback_model = fallback_model


# =============================================================================
# Context Types
# =============================================================================


@dataclass
class RetryContext:
    """Context passed through retry attempts.

    Attributes:
        model: The model being used.
        max_tokens_override: Override for max tokens (set on context overflow).
        thinking_config: Thinking configuration.
        fast_mode: Whether fast mode is enabled.
    """

    model: str
    max_tokens_override: int | None = None
    thinking_config: dict[str, Any] = field(default_factory=dict)
    fast_mode: bool | None = None


@dataclass
class RetryOptions:
    """Options for retry configuration.

    Attributes:
        max_retries: Maximum number of retry attempts.
        model: The model to use.
        fallback_model: Optional fallback model for 529 errors.
        thinking_config: Thinking configuration.
        fast_mode: Whether fast mode is enabled.
        signal: Optional abort signal.
        query_source: Source of the query for tracking.
        initial_consecutive_529_errors: Pre-seed consecutive 529 counter.
    """

    model: str
    max_retries: int | None = None
    fallback_model: str | None = None
    thinking_config: dict[str, Any] = field(default_factory=dict)
    fast_mode: bool | None = None
    signal: asyncio.AbstractEventLoop | None = None
    query_source: str | None = None
    initial_consecutive_529_errors: int = 0


# =============================================================================
# Query Source Classification
# =============================================================================

# Foreground query sources that should retry on 529.
# These are sources where the user IS blocking on the result.
FOREGROUND_529_RETRY_SOURCES: set[str] = {
    "repl_main_thread",
    "repl_main_thread:outputStyle:custom",
    "repl_main_thread:outputStyle:explanatory",
    "repl_main_thread:outputStyle:learning",
    "sdk",
    "agent:custom",
    "agent:default",
    "agent:builtin",
    "compact",
    "hook_agent",
    "hook_prompt",
    "verification_agent",
    "side_question",
    "auto_mode",
}


def should_retry_529(query_source: str | None) -> bool:
    """Determine if a 529 error should be retried based on query source.

    Args:
        query_source: The source of the query.

    Returns:
        True if 529 errors should be retried for this source.
    """
    # None/undefined -> retry (conservative for untagged call paths)
    if query_source is None:
        return True
    return query_source in FOREGROUND_529_RETRY_SOURCES


# =============================================================================
# Error Classification
# =============================================================================


def is_529_error(error: Exception) -> bool:
    """Check if an error is a 529 (Overloaded) error.

    Args:
        error: The exception to check.

    Returns:
        True if the error is a 529 error.
    """
    if isinstance(error, APIError):
        if error.status == 529:
            return True
        # Check message for overloaded_error type (streaming may not pass 529 status)
        msg = getattr(error, "message", "") or ""
        if '"type":"overloaded_error"' in msg:
            return True
    return False


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit (429) error.

    Args:
        error: The exception to check.

    Returns:
        True if the error is a 429 rate limit error.
    """
    if isinstance(error, APIError):
        return error.status == 429
    return False


def is_transient_capacity_error(error: Exception) -> bool:
    """Check if an error is a transient capacity error (429 or 529).

    Args:
        error: The exception to check.

    Returns:
        True if the error is transient and capacity-related.
    """
    return is_529_error(error) or is_rate_limit_error(error)


def is_connection_error(error: Exception) -> bool:
    """Check if an error is a connection error.

    Args:
        error: The exception to check.

    Returns:
        True if the error is a connection-related error.
    """
    # Check for common connection error patterns
    msg = str(error).lower()
    connection_indicators = [
        "connection",
        "timeout",
        "econnrefused",
        "econnreset",
        "enetunreach",
        "ehostunreach",
    ]
    return any(indicator in msg for indicator in connection_indicators)


def is_context_overflow_error(error: Exception) -> bool:
    """Check if an error is a context overflow error.

    Args:
        error: The exception to check.

    Returns:
        True if the error is a context overflow error.
    """
    if isinstance(error, APIError) and error.status == 400:
        msg = getattr(error, "message", "") or ""
        return "input length" in msg and "exceed context limit" in msg
    return False


def is_oauth_token_revoked_error(error: Exception) -> bool:
    """Check if an error is an OAuth token revoked error.

    Args:
        error: The exception to check.

    Returns:
        True if the error indicates OAuth token revocation.
    """
    if isinstance(error, APIError) and error.status == 403:
        msg = getattr(error, "message", "") or ""
        return "oauth token has been revoked" in msg.lower()
    return False


# =============================================================================
# Retry Delay Calculation
# =============================================================================


def get_retry_delay(
    attempt: int,
    retry_after_header: str | None = None,
    max_delay_ms: int = MAX_DELAY_MS,
) -> int:
    """Calculate the retry delay with exponential backoff and jitter.

    Args:
        attempt: The current attempt number (1-based).
        retry_after_header: Optional Retry-After header value in seconds.
        max_delay_ms: Maximum delay in milliseconds.

    Returns:
        Delay in milliseconds before the next retry.
    """
    # Honor Retry-After header if present
    if retry_after_header:
        try:
            seconds = int(retry_after_header)
            if seconds >= 0:
                return seconds * 1000
        except (ValueError, TypeError):
            pass

    # Exponential backoff: base * 2^(attempt-1)
    base_delay = BASE_DELAY_MS * (2 ** (attempt - 1))

    # Add jitter: 0-25% of base delay
    jitter = random.random() * 0.25 * base_delay

    return int(min(base_delay + jitter, max_delay_ms))


def get_retry_after_ms(error: Exception) -> int | None:
    """Extract Retry-After value from an error.

    Args:
        error: The exception to extract Retry-After from.

    Returns:
        Retry-After in milliseconds, or None if not present.
    """
    if isinstance(error, APIError):
        # Check headers dict
        headers = getattr(error, "headers", None)
        if headers and isinstance(headers, dict):
            retry_after = headers.get("retry-after")
            if retry_after:
                try:
                    return int(retry_after) * 1000
                except (ValueError, TypeError):
                    pass
    return None


def get_rate_limit_reset_delay_ms(error: Exception) -> int | None:
    """Get the delay until rate limit reset based on headers.

    Args:
        error: The exception to extract reset delay from.

    Returns:
        Delay in milliseconds until reset, or None.
    """
    if isinstance(error, APIError):
        headers = getattr(error, "headers", None)
        if headers and isinstance(headers, dict):
            reset_header = headers.get("anthropic-ratelimit-unified-reset")
            if reset_header:
                try:
                    reset_unix_sec = float(reset_header)
                    delay_ms = reset_unix_sec * 1000 - _current_time_ms()
                    if delay_ms > 0:
                        return min(delay_ms, PERSISTENT_RESET_CAP_MS)
                except (ValueError, TypeError):
                    pass
    return None


def _current_time_ms() -> int:
    """Get current time in milliseconds."""
    import time
    return int(time.time() * 1000)


# =============================================================================
# Context Overflow Parsing
# =============================================================================


@dataclass
class ContextOverflowData:
    """Parsed context overflow error data."""

    input_tokens: int
    max_tokens: int
    context_limit: int


def parse_max_tokens_context_overflow_error(error: Exception) -> ContextOverflowData | None:
    """Parse max tokens context overflow error.

    Args:
        error: The exception to parse.

    Returns:
        ContextOverflowData if parsing succeeded, else None.
    """
    if not isinstance(error, APIError) or error.status != 400:
        return None

    msg = getattr(error, "message", "") or ""
    if "input length and `max_tokens` exceed context limit" not in msg:
        return None

    # Example: "input length and `max_tokens` exceed context limit: 188059 + 20000 > 200000"
    import re
    pattern = r"input length and `max_tokens` exceed context limit: (\d+) \+ (\d+) > (\d+)"
    match = re.search(pattern, msg)
    if not match:
        return None

    try:
        input_tokens = int(match.group(1))
        max_tokens = int(match.group(2))
        context_limit = int(match.group(3))
        return ContextOverflowData(
            input_tokens=input_tokens,
            max_tokens=max_tokens,
            context_limit=context_limit,
        )
    except (ValueError, IndexError):
        return None


# =============================================================================
# Should Retry Decision
# =============================================================================


def should_retry(error: Exception, persistent_enabled: bool = False) -> bool:
    """Determine if an error should trigger a retry.

    Args:
        error: The exception to evaluate.
        persistent_enabled: Whether persistent retry mode is enabled.

    Returns:
        True if the error is retryable.
    """
    # Never retry non-API errors
    if not isinstance(error, APIError):
        return False

    # Persistent mode: 429/529 always retryable
    if persistent_enabled and is_transient_capacity_error(error):
        return True

    status = getattr(error, "status", None)

    # Connection errors are always retryable
    if isinstance(error, APIError) and status is None:
        # Connection errors may not have a status
        msg = str(error).lower()
        if "connection" in msg or "timeout" in msg:
            return True

    if status is None:
        return False

    # Retry on request timeouts
    if status == 408:
        return True

    # Retry on lock timeouts
    if status == 409:
        return True

    # Retry on rate limits (non-subscriber)
    if status == 429:
        # TODO: Check if user is ClaudeAI subscriber
        return True

    # Retry on 529 overload errors
    if status == 529:
        return True

    # Retry on auth errors (after clearing cache)
    if status == 401:
        return True

    # Retry on 403 token revoked
    if is_oauth_token_revoked_error(error):
        return True

    # Retry on server errors
    if status >= 500:
        return True

    # Retry on context overflow
    return bool(parse_max_tokens_context_overflow_error(error))


# =============================================================================
# Retry Implementation
# =============================================================================

T = TypeVar("T")


async def with_retry(
    operation: Callable[[int, RetryContext], T],
    options: RetryOptions,
) -> T:
    """Execute an operation with retry logic.

    This implements exponential backoff with jitter for transient errors,
    special handling for 529 overload errors and rate limits.

    Args:
        operation: Async function to execute. Takes (attempt, context) and returns T.
        options: Retry configuration options.

    Returns:
        The result of the operation.

    Raises:
        CannotRetryError: If the operation fails after all retries.
        FallbackTriggeredError: If model fallback is triggered.
    """
    max_retries = options.max_retries if options.max_retries is not None else DEFAULT_MAX_RETRIES
    retry_context = RetryContext(
        model=options.model,
        thinking_config=options.thinking_config,
        fast_mode=options.fast_mode,
    )

    consecutive_529_errors = options.initial_consecutive_529_errors
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 2):  # +1 for final attempt
        try:
            return await operation(attempt, retry_context)
        except Exception as error:  # noqa: BLE001
            last_error = error if isinstance(error, Exception) else Exception(str(error))

            # Check if we should retry
            if not should_retry(last_error):
                raise CannotRetryError(last_error, retry_context) from last_error

            # Track consecutive 529 errors
            if is_529_error(last_error):
                consecutive_529_errors += 1
                if consecutive_529_errors >= MAX_529_RETRIES:
                    # Check for fallback model
                    if options.fallback_model:
                        raise FallbackTriggeredError(
                            options.model,
                            options.fallback_model,
                        ) from last_error
                    raise CannotRetryError(last_error, retry_context) from last_error

            # Calculate delay
            retry_after = None
            if isinstance(last_error, APIError):
                retry_after = get_retry_after_ms(last_error)

            delay_ms = get_retry_delay(attempt, retry_after)

            # Wait before retrying
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    # Exhausted retries
    if last_error:
        raise CannotRetryError(last_error, retry_context)
    raise CannotRetryError(Exception("Unknown error after retries"), retry_context)


def calculate_context_overflow_adjustment(
    overflow: ContextOverflowData,
    thinking_config: dict[str, Any],
) -> int:
    """Calculate adjusted max_tokens after context overflow.

    Args:
        overflow: Parsed context overflow data.
        thinking_config: Thinking configuration.

    Returns:
        Adjusted max_tokens value.
    """
    safety_buffer = 1000
    available_context = max(
        0,
        overflow.context_limit - overflow.input_tokens - safety_buffer,
    )

    if available_context < FLOOR_OUTPUT_TOKENS:
        available_context = FLOOR_OUTPUT_TOKENS

    # Ensure enough tokens for thinking + at least 1 output token
    min_required = 1
    if thinking_config.get("type") == "enabled":
        min_required = max(min_required, thinking_config.get("budget_tokens", 0) + 1)

    return max(FLOOR_OUTPUT_TOKENS, available_context, min_required)


# =============================================================================
# Sync Retry (for non-async contexts)
# =============================================================================


def with_retry_sync(
    operation: Callable[[int, RetryContext], T],
    options: RetryOptions,
) -> T:
    """Execute a synchronous operation with retry logic.

    Args:
        operation: Function to execute. Takes (attempt, context) and returns T.
        options: Retry configuration options.

    Returns:
        The result of the operation.

    Raises:
        CannotRetryError: If the operation fails after all retries.
        FallbackTriggeredError: If model fallback is triggered.
    """
    max_retries = options.max_retries if options.max_retries is not None else DEFAULT_MAX_RETRIES
    retry_context = RetryContext(
        model=options.model,
        thinking_config=options.thinking_config,
        fast_mode=options.fast_mode,
    )

    consecutive_529_errors = options.initial_consecutive_529_errors
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 2):
        try:
            return operation(attempt, retry_context)
        except Exception as error:  # noqa: BLE001
            last_error = error if isinstance(error, Exception) else Exception(str(error))

            if not should_retry(last_error):
                raise CannotRetryError(last_error, retry_context) from last_error

            if is_529_error(last_error):
                consecutive_529_errors += 1
                if consecutive_529_errors >= MAX_529_RETRIES:
                    if options.fallback_model:
                        raise FallbackTriggeredError(
                            options.model,
                            options.fallback_model,
                        ) from last_error
                    raise CannotRetryError(last_error, retry_context) from last_error

            retry_after = None
            if isinstance(last_error, APIError):
                retry_after = get_retry_after_ms(last_error)

            delay_ms = get_retry_delay(attempt, retry_after)

            if delay_ms > 0:
                time.sleep(delay_ms / 1000)

    if last_error:
        raise CannotRetryError(last_error, retry_context)
    raise CannotRetryError(Exception("Unknown error after retries"), retry_context)
