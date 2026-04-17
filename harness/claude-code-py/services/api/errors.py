"""
API error types and utilities for Claude Code services.

This module defines custom exception classes and utilities for API-related errors:
- APIError: Base class for all API errors
- RateLimitError: Raised when API rate limit is exceeded (429)
- AuthError: Raised when authentication fails (401/403)
- PromptTooLongError: Raised when prompt exceeds token limits
- ConnectionError: Raised when connection fails
- Error classification and formatting utilities
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# =============================================================================
# API Error Classes
# =============================================================================


class APIError(Exception):
    """Base exception for all API-related errors.

    Attributes:
        status: HTTP status code of the error response.
        message: Error message describing the failure.
        headers: Response headers from the API (optional).
        body: Response body from the API (optional).
    """

    def __init__(
        self,
        message: str,
        status: int | None = None,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status: int | None = status
        self.message: str = message
        self.headers: dict[str, str] | None = headers
        self.body: str | None = body

    def __repr__(self) -> str:
        parts = [f"APIError({self.message!r}"]
        if self.status is not None:
            parts.append(f", status={self.status}")
        parts.append(")")
        return "".join(parts)


class RateLimitError(APIError):
    """Raised when an API rate limit is exceeded (HTTP 429).

    Inherits from APIError. The status is always 429 for this error type.
    """

    def __init__(
        self,
        message: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status=429, headers=headers, body=body)
        self.retry_after: int | None = retry_after

    def __repr__(self) -> str:
        parts = [f"RateLimitError({self.message!r}"]
        if self.retry_after is not None:
            parts.append(f", retry_after={self.retry_after}")
        parts.append(")")
        return "".join(parts)


class AuthError(APIError):
    """Raised when API authentication fails (HTTP 401 or 403).

    Inherits from APIError. Used for invalid API keys, expired tokens,
    and organization-disabled errors.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message, status=status, headers=headers, body=body)

    def __repr__(self) -> str:
        parts = [f"AuthError({self.message!r}"]
        if self.status is not None:
            parts.append(f", status={self.status}")
        parts.append(")")
        return "".join(parts)


class PromptTooLongError(APIError):
    """Raised when the prompt exceeds the model's token limit.

    Inherits from APIError. The status is typically 400 for this error type.
    Contains parsed token count information when available.
    """

    def __init__(
        self,
        message: str,
        *,
        actual_tokens: int | None = None,
        limit_tokens: int | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message, status=400, headers=headers, body=body)
        self.actual_tokens: int | None = actual_tokens
        self.limit_tokens: int | None = limit_tokens

    @property
    def token_gap(self) -> int | None:
        """Return how many tokens over the limit, or None if not parseable."""
        if self.actual_tokens is not None and self.limit_tokens is not None:
            gap = self.actual_tokens - self.limit_tokens
            return gap if gap > 0 else None
        return None

    def __repr__(self) -> str:
        parts = [f"PromptTooLongError({self.message!r}"]
        if self.actual_tokens is not None:
            parts.append(f", actual_tokens={self.actual_tokens}")
        if self.limit_tokens is not None:
            parts.append(f", limit_tokens={self.limit_tokens}")
        parts.append(")")
        return "".join(parts)


class ConnectionError(APIError):
    """Raised when connection to the API fails.

    Inherits from APIError. Used for network failures, timeouts,
    and SSL/TLS errors.
    """

    def __init__(
        self,
        message: str = "Connection error",
        *,
        status: int | None = None,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message, status=status, headers=headers, body=body)
        self.code: str | None = code

    def __repr__(self) -> str:
        parts = [f"ConnectionError({self.message!r}"]
        if self.code is not None:
            parts.append(f", code={self.code!r}")
        parts.append(")")
        return "".join(parts)


class ConnectionTimeoutError(ConnectionError):
    """Raised when connection to the API times out."""

    def __init__(
        self,
        message: str = "Connection timeout",
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message, headers=headers, body=body, code=code)


# =============================================================================
# Error Classification
# =============================================================================


# SSL/TLS error codes from OpenSSL
_SSL_ERROR_CODES: set[str] = {
    # Certificate verification errors
    "UNABLE_TO_VERIFY_LEAF_SIGNATURE",
    "UNABLE_TO_GET_ISSUER_CERT",
    "UNABLE_TO_GET_ISSUER_CERT_LOCALLY",
    "CERT_SIGNATURE_FAILURE",
    "CERT_NOT_YET_VALID",
    "CERT_HAS_EXPIRED",
    "CERT_REVOKED",
    "CERT_REJECTED",
    "CERT_UNTRUSTED",
    # Self-signed certificate errors
    "DEPTH_ZERO_SELF_SIGNED_CERT",
    "SELF_SIGNED_CERT_IN_CHAIN",
    # Chain errors
    "CERT_CHAIN_TOO_LONG",
    "PATH_LENGTH_EXCEEDED",
    # Hostname/altname errors
    "ERR_TLS_CERT_ALTNAME_INVALID",
    "HOSTNAME_MISMATCH",
    # TLS handshake errors
    "ERR_TLS_HANDSHAKE_TIMEOUT",
    "ERR_SSL_WRONG_VERSION_NUMBER",
    "ERR_SSL_DECRYPTION_FAILED_OR_BAD_RECORD_MAC",
}


@dataclass
class ConnectionErrorDetails:
    """Details extracted from a connection error."""

    code: str
    message: str
    is_ssl_error: bool


def extract_connection_error_details(
    error: BaseException,
) -> ConnectionErrorDetails | None:
    """Extract connection error details from an error's cause chain.

    Walks the cause chain to find the root error with its code and message.

    Args:
        error: The error to analyze.

    Returns:
        ConnectionErrorDetails if a connection error was found, else None.
    """
    if error is None:
        return None

    current: BaseException | None = error
    max_depth = 5
    depth = 0

    while current is not None and depth < max_depth:
        code = getattr(current, "code", None)
        msg = str(getattr(current, "message", "") or "")

        if isinstance(code, str) and code:
            is_ssl_error = code in _SSL_ERROR_CODES
            return ConnectionErrorDetails(
                code=code,
                message=msg,
                is_ssl_error=is_ssl_error,
            )

        cause = getattr(current, "cause", None)
        if cause is not None and cause is not current:
            current = cause if isinstance(cause, BaseException) else None
            depth += 1
        else:
            break

    return None


def get_ssl_error_hint(error: BaseException) -> str | None:
    """Get an actionable hint for SSL/TLS errors.

    Provides guidance for enterprise users behind TLS-intercepting proxies.

    Args:
        error: The error to analyze.

    Returns:
        A hint string for SSL errors, or None if not an SSL error.
    """
    details = extract_connection_error_details(error)
    if details is None or not details.is_ssl_error:
        return None
    return (
        f"SSL certificate error ({details.code}). "
        "If you are behind a corporate proxy or TLS-intercepting firewall, "
        "set NODE_EXTRA_CA_CERTS to your CA bundle path, or ask IT to allowlist "
        "*.anthropic.com. Run /doctor for details."
    )


def sanitize_message_html(message: str) -> str:
    """Strip HTML content from error messages.

    Detects HTML (e.g., CloudFlare error pages) and extracts the title.

    Args:
        message: The message to sanitize.

    Returns:
        The title extracted from HTML, or the original message if no HTML found.
    """
    if "<!DOCTYPE html" in message or "<html" in message:
        match = re.search(r"<title>([^<]+)</title>", message)
        if match:
            return match.group(1).strip()
        return ""
    return message


def format_api_error(error: Exception) -> str:
    """Format an API error into a user-friendly message.

    Args:
        error: The exception to format.

    Returns:
        A human-readable error message.
    """
    # Extract connection error details
    connection_details = extract_connection_error_details(error)
    error_message = str(error) if not isinstance(error, BaseException) else ""

    # Check for timeout errors
    if connection_details is not None:
        code = connection_details.code
        is_ssl = connection_details.is_ssl_error

        if code == "ETIMEDOUT":
            return "Request timed out. Check your internet connection and proxy settings"

        if is_ssl:
            if code in ("UNABLE_TO_VERIFY_LEAF_SIGNATURE", "UNABLE_TO_GET_ISSUER_CERT", "UNABLE_TO_GET_ISSUER_CERT_LOCALLY"):
                return "Unable to connect to API: SSL certificate verification failed. Check your proxy or corporate SSL certificates"
            if code == "CERT_HAS_EXPIRED":
                return "Unable to connect to API: SSL certificate has expired"
            if code == "CERT_REVOKED":
                return "Unable to connect to API: SSL certificate has been revoked"
            if code in ("DEPTH_ZERO_SELF_SIGNED_CERT", "SELF_SIGNED_CERT_IN_CHAIN"):
                return "Unable to connect to API: Self-signed certificate detected. Check your proxy or corporate SSL certificates"
            if code in ("ERR_TLS_CERT_ALTNAME_INVALID", "HOSTNAME_MISMATCH"):
                return "Unable to connect to API: SSL certificate hostname mismatch"
            if code == "CERT_NOT_YET_VALID":
                return "Unable to connect to API: SSL certificate is not yet valid"
            return f"Unable to connect to API: SSL error ({code})"

    if error_message == "Connection error.":
        if connection_details is not None:
            return f"Unable to connect to API ({connection_details.code})"
        return "Unable to connect to API. Check your internet connection"

    # Handle APIError with status
    if isinstance(error, APIError):
        if not error_message:
            nested = _extract_nested_error_message(error)
            if nested:
                return nested
            status = error.status
            return f"API error (status {status if status is not None else 'unknown'})"

        sanitized = sanitize_message_html(error_message)
        if sanitized and sanitized != error_message:
            return sanitized
        return error_message

    # Generic error
    if error_message:
        return error_message
    return "An unexpected error occurred"


def _extract_nested_error_message(error: APIError) -> str | None:
    """Extract message from a nested error structure.

    Handles shapes like:
    - { error: { message: "..." } } (Bedrock)
    - { error: { error: { message: "..." } } } (Standard Anthropic API)

    Args:
        error: The API error to extract from.

    Returns:
        The extracted message or None.
    """
    body = getattr(error, "body", None)
    if body is None:
        return None

    # Try to parse as JSON
    import json
    try:
        data = json.loads(body) if isinstance(body, str) else body
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(data, dict):
        return None

    error_obj = data.get("error")
    if not isinstance(error_obj, dict):
        return None

    # Standard Anthropic API: { error: { error: { message } } }
    inner = error_obj.get("error")
    if isinstance(inner, dict):
        msg = inner.get("message")
        if isinstance(msg, str) and msg:
            sanitized = sanitize_message_html(msg)
            if sanitized:
                return sanitized

    # Bedrock shape: { error: { message } }
    msg = error_obj.get("message")
    if isinstance(msg, str) and msg:
        sanitized = sanitize_message_html(msg)
        if sanitized:
            return sanitized

    return None


# =============================================================================
# Error Classification Helpers
# =============================================================================


def is_abort_error(error: BaseException | None) -> bool:
    """Check if an error is an abort-shaped error.

    Handles AbortError, DOMException AbortError, and SDK abort errors.

    Args:
        error: The error to check.

    Returns:
        True if the error is an abort error.
    """
    if error is None:
        return False
    if isinstance(error, Exception):
        name = getattr(error, "name", None)
        if name == "AbortError":
            return True
    return False


def has_exact_error_message(error: BaseException | None, message: str) -> bool:
    """Check if an error has an exact message.

    Args:
        error: The error to check.
        message: The expected message.

    Returns:
        True if the error has the exact message.
    """
    if error is None:
        return False
    return getattr(error, "message", None) == message


def to_error(e: Any) -> Exception:
    """Convert an unknown value to an Exception.

    Args:
        e: The value to convert.

    Returns:
        An Exception instance.
    """
    if isinstance(e, Exception):
        return e
    return Exception(str(e))


def error_message(e: Any) -> str:
    """Extract a string message from an error.

    Args:
        e: The error-like value.

    Returns:
        The error message as a string.
    """
    if isinstance(e, Exception):
        msg = getattr(e, "message", None)
        if isinstance(msg, str):
            return msg
    return str(e) if e is not None else ""


def get_errno_code(e: Any) -> str | None:
    """Extract the errno code from an error.

    Args:
        e: The error to extract from.

    Returns:
        The errno code or None.
    """
    if e is None:
        return None
    if isinstance(e, dict):
        code = e.get("code")
        if isinstance(code, str):
            return code
        return None
    obj = getattr(e, "__dict__", None) if isinstance(e, object) else None
    if obj is not None:
        code = obj.get("code")
        if isinstance(code, str):
            return code
    return None


def is_enoent(e: Any) -> bool:
    """Check if an error is ENOENT (file not found).

    Args:
        e: The error to check.

    Returns:
        True if the error is ENOENT.
    """
    return get_errno_code(e) == "ENOENT"


def get_errno_path(e: Any) -> str | None:
    """Extract the filesystem path from an error.

    Args:
        e: The error to extract from.

    Returns:
        The path or None.
    """
    if e is None:
        return None
    if isinstance(e, dict):
        path = e.get("path")
        if isinstance(path, str):
            return path
        return None
    obj = getattr(e, "__dict__", None)
    if obj is not None:
        path = obj.get("path")
        if isinstance(path, str):
            return path
    return None


def is_fs_inaccessible(e: Any) -> bool:
    """Check if an error means the path is missing or inaccessible.

    Args:
        e: The error to check.

    Returns:
        True if the error indicates filesystem inaccessibility.
    """
    code = get_errno_code(e)
    return code in ("ENOENT", "EACCES", "EPERM", "ENOTDIR", "ELOOP")


# =============================================================================
# API Error Classification
# =============================================================================


# Error message constants
API_ERROR_MESSAGE_PREFIX = "API Error"
PROMPT_TOO_LONG_ERROR_MESSAGE = "Prompt is too long"
CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE = "Credit balance is too low"
INVALID_API_KEY_ERROR_MESSAGE = "Not logged in · Please run /login"
INVALID_API_KEY_ERROR_MESSAGE_EXTERNAL = "Invalid API key · Fix external API key"
API_TIMEOUT_ERROR_MESSAGE = "Request timed out"
TOKEN_REVOKED_ERROR_MESSAGE = "OAuth token revoked · Please run /login"
CCR_AUTH_ERROR_MESSAGE = "Authentication error · This may be a temporary network issue, please try again"
REPEATED_529_ERROR_MESSAGE = "Repeated 529 Overloaded errors"
CUSTOM_OFF_SWITCH_MESSAGE = "Opus is experiencing high load, please use /model to switch to Sonnet"


def is_prompt_too_long_message(message: str) -> bool:
    """Check if a message indicates a prompt-too-long error.

    Args:
        message: The error message to check.

    Returns:
        True if the message is about prompt being too long.
    """
    return message.lower().startswith(PROMPT_TOO_LONG_ERROR_MESSAGE.lower())


def parse_prompt_too_long_token_counts(raw_message: str) -> tuple[int | None, int | None]:
    """Parse token counts from a prompt-too-long error message.

    Args:
        raw_message: The raw error message.

    Returns:
        Tuple of (actual_tokens, limit_tokens) or (None, None).
    """
    match = re.search(
        r"prompt is too long[^0-9]*(\d+)\s*tokens?\s*>\s*(\d+)",
        raw_message,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def is_media_size_error(raw: str) -> bool:
    """Check if an error is a media size rejection.

    Args:
        raw: The raw error message.

    Returns:
        True if the error is about media size.
    """
    has_image = "image exceeds" in raw.lower() and "maximum" in raw.lower()
    has_dimensions = "image dimensions exceed" in raw.lower() and "many-image" in raw.lower()
    has_pdf = bool(re.search(r"maximum of \d+ PDF pages", raw))
    return has_image or has_dimensions or has_pdf


# API Error Classification types
APIErrorKind = str  # Literal["auth", "timeout", "network", "http", "other"]


@dataclass
class ClassifiedAPIError:
    """Classified API error with kind and details."""

    kind: APIErrorKind
    message: str
    status: int | None = None


def classify_api_error(error: Exception | None) -> ClassifiedAPIError:
    """Classify an API error into a specific error type.

    Args:
        error: The exception to classify.

    Returns:
        ClassifiedAPIError with kind and message.
    """
    if error is None:
        return ClassifiedAPIError(kind="other", message="")

    error_msg = error_message(error)

    # Aborted requests
    if error_msg == "Request was aborted.":
        return ClassifiedAPIError(kind="aborted", message=error_msg)

    # Timeout errors
    if isinstance(error, ConnectionTimeoutError):
        return ClassifiedAPIError(kind="api_timeout", message=error_msg)
    if "timeout" in error_msg.lower():
        return ClassifiedAPIError(kind="api_timeout", message=error_msg)

    # Repeated 529 errors
    if REPEATED_529_ERROR_MESSAGE in error_msg:
        return ClassifiedAPIError(kind="repeated_529", message=error_msg)

    # Capacity off switch
    if CUSTOM_OFF_SWITCH_MESSAGE in error_msg:
        return ClassifiedAPIError(kind="capacity_off_switch", message=error_msg)

    # Rate limiting
    if isinstance(error, RateLimitError):
        return ClassifiedAPIError(kind="rate_limit", message=error_msg, status=error.status)

    # Server overload (529)
    if isinstance(error, APIError) and error.status == 529:
        return ClassifiedAPIError(kind="server_overload", message=error_msg, status=error.status)

    # Prompt/content size errors
    if is_prompt_too_long_message(error_msg):
        return ClassifiedAPIError(kind="prompt_too_long", message=error_msg)

    # PDF errors
    if re.search(r"maximum of \d+ PDF pages", error_msg):
        return ClassifiedAPIError(kind="pdf_too_large", message=error_msg)
    if "password protected" in error_msg.lower() and "pdf" in error_msg.lower():
        return ClassifiedAPIError(kind="pdf_password_protected", message=error_msg)

    # Image size errors
    if isinstance(error, APIError) and error.status == 400:
        if "image exceeds" in error_msg.lower() and "maximum" in error_msg.lower():
            return ClassifiedAPIError(kind="image_too_large", message=error_msg, status=error.status)
        if "image dimensions exceed" in error_msg.lower() and "many-image" in error_msg.lower():
            return ClassifiedAPIError(kind="image_too_large", message=error_msg, status=error.status)
        if "tool_use" in error_msg.lower() and "tool_result" in error_msg.lower():
            return ClassifiedAPIError(kind="tool_use_mismatch", message=error_msg, status=error.status)
        if "invalid model" in error_msg.lower():
            return ClassifiedAPIError(kind="invalid_model", message=error_msg, status=error.status)

    # Credit/billing errors
    if "credit balance" in error_msg.lower() and "too low" in error_msg.lower():
        return ClassifiedAPIError(kind="credit_balance_low", message=error_msg)

    # Authentication errors
    if "x-api-key" in error_msg.lower():
        return ClassifiedAPIError(kind="invalid_api_key", message=error_msg)
    if "token" in error_msg.lower() and ("revoked" in error_msg.lower() or "expired" in error_msg.lower()):
        return ClassifiedAPIError(kind="token_revoked", message=error_msg)

    # Generic auth errors
    if isinstance(error, AuthError):
        return ClassifiedAPIError(kind="auth_error", message=error_msg, status=error.status)

    # Generic API errors by status
    if isinstance(error, APIError):
        status = error.status
        if status is not None:
            if status >= 500:
                return ClassifiedAPIError(kind="server_error", message=error_msg, status=status)
            if status >= 400:
                return ClassifiedAPIError(kind="client_error", message=error_msg, status=status)

    # Connection errors
    if isinstance(error, ConnectionError):
        if connection_details := extract_connection_error_details(error):
            if connection_details.is_ssl_error:
                return ClassifiedAPIError(kind="ssl_cert_error", message=error_msg)
        return ClassifiedAPIError(kind="connection_error", message=error_msg)

    return ClassifiedAPIError(kind="unknown", message=error_msg)


def starts_with_api_error_prefix(text: str) -> bool:
    """Check if text starts with the API error prefix.

    Args:
        text: The text to check.

    Returns:
        True if text starts with an API error prefix.
    """
    return (
        text.startswith(API_ERROR_MESSAGE_PREFIX) or
        text.startswith(f"Please run /login · {API_ERROR_MESSAGE_PREFIX}")
    )
