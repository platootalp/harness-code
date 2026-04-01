"""Model module error types.

Defines exceptions for model invocation failures.
"""

from __future__ import annotations

from typing import Any


class ModelError(Exception):
    """Base exception for model-related errors."""

    error_code: str = "MODEL_000"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize model error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ModelInvocationError(ModelError):
    """Raised when a model invocation fails."""

    error_code = "MODEL_001"

    def __init__(
        self,
        message: str = "Model invocation failed",
        model: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize invocation error.

        Args:
            message: Error message.
            model: Model that was being invoked.
            details: Additional error details.
        """
        super().__init__(message, details)
        self.model = model


class ModelNotFoundError(ModelError):
    """Raised when a requested model is not found."""

    error_code = "MODEL_002"

    def __init__(
        self,
        message: str = "Model not found",
        model: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize not found error.

        Args:
            message: Error message.
            model: Model that was not found.
            details: Additional error details.
        """
        super().__init__(message, details)
        self.model = model


class InvalidRequestError(ModelError):
    """Raised when a model request is invalid."""

    error_code = "MODEL_003"

    def __init__(
        self,
        message: str = "Invalid request",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize invalid request error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message, details)


class ResponseParseError(ModelError):
    """Raised when parsing a model response fails."""

    error_code = "MODEL_004"

    def __init__(
        self,
        message: str = "Failed to parse model response",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize parse error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message, details)


class RateLimitError(ModelError):
    """Raised when rate limit is exceeded."""

    error_code = "MODEL_005"

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message.
            retry_after: Seconds to wait before retrying.
            details: Additional error details.
        """
        super().__init__(message, details)
        self.retry_after = retry_after


class AuthenticationError(ModelError):
    """Raised when authentication fails."""

    error_code = "MODEL_006"

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize authentication error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message, details)


class CircuitBreakerOpenError(ModelError):
    """Raised when circuit breaker is open."""

    error_code = "MODEL_007"

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize circuit breaker open error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message, details)
