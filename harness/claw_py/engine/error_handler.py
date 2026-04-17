"""
Error handling utilities and QueryErrorHandler for the Claude Code engine.

Provides:
- Error type definitions and utilities
- QueryErrorHandler: handles error classification, normalization, and recovery
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Error Types
# =============================================================================


class ClaudeError(Exception):
    """Base error class for Claude Code errors."""

    pass


class MalformedCommandError(Exception):
    """Error raised when a command cannot be parsed."""

    pass


class AbortError(Exception):
    """Error raised when an operation is aborted."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.name = "AbortError"


class ConfigParseError(Exception):
    """Error raised when a configuration file cannot be parsed."""

    def __init__(
        self,
        message: str,
        file_path: str,
        default_config: Any,
    ) -> None:
        super().__init__(message)
        self.name = "ConfigParseError"
        self.file_path = file_path
        self.default_config = default_config


@dataclass
class ShellError:
    """Error raised when a shell command fails."""

    stdout: str
    stderr: str
    code: int
    interrupted: bool

    def __str__(self) -> str:
        return f"Shell command failed (exit {self.code})"


class TeleportOperationError(Exception):
    """Error raised during teleport operations."""

    def __init__(self, message: str, formatted_message: str) -> None:
        super().__init__(message)
        self.name = "TeleportOperationError"
        self.formatted_message = formatted_message


class TelemetrySafeError(Exception):
    """Error with a message that is safe to log to telemetry.

    Args:
        message: The full message shown to user/logs.
        telemetry_message: Optional separate message for telemetry.
    """

    def __init__(self, message: str, telemetry_message: str | None = None) -> None:
        super().__init__(message)
        self.name = "TelemetrySafeError"
        self.telemetry_message = telemetry_message if telemetry_message is not None else message


# =============================================================================
# Error Utilities
# =============================================================================


def is_abort_error(e: Any) -> bool:
    """Check if an error is an abort-shaped error.

    Matches:
    - AbortError instances
    - AbortController.abort() DOMException (name === 'AbortError')

    Args:
        e: The caught error to check.

    Returns:
        True if this is an abort error.
    """
    if e is None:
        return False
    if isinstance(e, AbortError):
        return True
    return isinstance(e, Exception) and getattr(e, "name", None) == "AbortError"


def has_exact_error_message(error: Any, message: str) -> bool:
    """Check if an error has an exact message match.

    Args:
        error: The error to check.
        message: The expected message.

    Returns:
        True if error.message exactly matches message.
    """
    if error is None:
        return False
    if isinstance(error, Exception):
        return error.args[0] == message if error.args else False
    return False


def to_error(e: Any) -> Exception:
    """Normalize an unknown value into an Exception.

    Args:
        e: Any value to normalize.

    Returns:
        An Exception instance.
    """
    if isinstance(e, Exception):
        return e
    return Exception(str(e))


def error_message(e: Any) -> str:
    """Extract a String message from an error-like value.

    Args:
        e: The error to extract from.

    Returns:
        The error message String.
    """
    if isinstance(e, Exception):
        return str(e.args[0]) if e.args else ""
    return str(e)


def get_errno_code(e: Any) -> str | None:
    """Extract the errno code (e.g., 'ENOENT', 'EACCES') from an error.

    Args:
        e: The error to inspect.

    Returns:
        The errno code String, or None if not present.
    """
    if e is None:
        return None
    if hasattr(e, "code") and isinstance(e.code, str):
        return e.code
    return None


def is_enoent(e: Any) -> bool:
    """Check if an error is ENOENT (file/directory does not exist).

    Args:
        e: The error to check.

    Returns:
        True if the error code is ENOENT.
    """
    return get_errno_code(e) == "ENOENT"


def get_errno_path(e: Any) -> str | None:
    """Extract the filesystem path from an ENOENT/EACCES error.

    Args:
        e: The error to inspect.

    Returns:
        The path that triggered the error, or None.
    """
    if e is None:
        return None
    if hasattr(e, "path") and isinstance(e.path, str):
        return e.path
    return None


def short_error_stack(e: Any, max_frames: int = 5) -> str:
    """Extract error message + top N stack frames.

    Produces a compact error String suitable for tool results where
    full stacks are too verbose for context tokens.

    Args:
        e: The error to format.
        max_frames: Maximum number of stack frames to include (default 5).

    Returns:
        Compact error String with message and limited stack frames.
    """
    if not isinstance(e, Exception):
        return str(e)
    msg = str(e)
    if e.__traceback__ is None:
        return msg
    # Build a compact stack String
    frames: list[str] = []
    tb: Any = e.__traceback__
    while tb is not None and len(frames) < max_frames:
        frame = tb.tb_frame
        name = frame.f_code.co_name
        filename = frame.f_code.co_filename
        lineno = tb.tb_lineno
        frames.append(f"  at {name} ({filename}:{lineno})")
        tb = tb.tb_next
    if not frames:
        return msg
    return f"{msg}\n" + "\n".join(frames)


def is_fs_inaccessible(e: Any) -> bool:
    """Check if an error means a path is missing or inaccessible.

    Covers:
    - ENOENT: path does not exist
    - EACCES: permission denied
    - EPERM: operation not permitted
    - ENOTDIR: a path component is not a directory
    - ELOOP: too many symlink levels (circular symlinks)

    Args:
        e: The error to check.

    Returns:
        True if the error indicates filesystem inaccessibility.
    """
    code = get_errno_code(e)
    return code in {"ENOENT", "EACCES", "EPERM", "ENOTDIR", "ELOOP"}


# =============================================================================
# API Error Classification
# =============================================================================


AxiosErrorKind = Literal["auth", "timeout", "network", "http", "other"]


def classify_axios_error(e: Any) -> dict[str, Any]:
    """Classify a caught error from an HTTP request.

    Categorizes errors into auth/timeout/network/http/other buckets
    for appropriate handling.

    Args:
        e: The caught error.

    Returns:
        A dict with 'kind', optional 'status', and 'message' fields.
    """
    msg = error_message(e)

    # Check for axios error marker
    if e is None or not hasattr(e, "is_axios_error"):
        return {"kind": "other", "message": msg}

    if not getattr(e, "is_axios_error", False):
        return {"kind": "other", "message": msg}

    response = getattr(e, "response", None)
    if response is None:
        status: int | None = None
    elif isinstance(response, dict):
        status = response.get("status")  # type: ignore[assignment]
    else:
        status = getattr(response, "status", None)  # type: ignore[assignment]
    code = getattr(e, "code", None)

    if status in {401, 403}:
        return {"kind": "auth", "status": status, "message": msg}
    if code == "ECONNABORTED":
        return {"kind": "timeout", "status": status, "message": msg}
    if code in {"ECONNREFUSED", "ENOTFOUND"}:
        return {"kind": "network", "status": status, "message": msg}
    return {"kind": "http", "status": status, "message": msg}


# =============================================================================
# Query Error Handler
# =============================================================================


ErrorHandlerCallback = Callable[[Exception], None]
AbortCallback = Callable[[], None]


class QueryErrorHandler:
    """Handles errors during query execution.

    Provides error classification, normalization, and callback-based
    error recovery for the QueryEngine.

    Attributes:
        on_error: Called for each non-abort error.
        on_abort: Called when an AbortError is raised.
        on_retry: Called before retrying after a retryable error.
        on_max_retries: Called when max retries is exceeded.
    """

    def __init__(
        self,
        on_error: ErrorHandlerCallback | None = None,
        on_abort: AbortCallback | None = None,
        on_retry: ErrorHandlerCallback | None = None,
        on_max_retries: ErrorHandlerCallback | None = None,
    ) -> None:
        """Initialize the error handler with optional callbacks.

        Args:
            on_error: Called for each non-abort error encountered.
            on_abort: Called when an operation is aborted.
            on_retry: Called before retrying after a retryable error.
            on_max_retries: Called when maximum retries is exceeded.
        """
        self.on_error = on_error
        self.on_abort = on_abort
        self.on_retry = on_retry
        self.on_max_retries = on_max_retries
        self._retry_count = 0
        self._max_retries = 3

    @property
    def retry_count(self) -> int:
        """Number of retries attempted."""
        return self._retry_count

    @property
    def max_retries(self) -> int:
        """Maximum number of retries allowed."""
        return self._max_retries

    @max_retries.setter
    def max_retries(self, value: int) -> None:
        """Set the maximum number of retries."""
        self._max_retries = max(0, value)

    def reset(self) -> None:
        """Reset retry counter."""
        self._retry_count = 0

    def handle_error(self, error: Any) -> None:
        """Handle an error by classifying and dispatching to callbacks.

        Args:
            error: The error that was raised.
        """
        err = to_error(error)

        if is_abort_error(err):
            if self.on_abort is not None:
                self.on_abort()
            return

        # Classify the error for logging/debugging
        self._classify_error(err)
        if self.on_error is not None:
            self.on_error(err)

    def should_retry(self, error: Any) -> bool:
        """Determine if an error is retryable.

        Args:
            error: The error to check.

        Returns:
            True if the error should trigger a retry.
        """
        if self._retry_count >= self._max_retries:
            return False

        kind = classify_axios_error(error)["kind"]

        # Retry timeout, network, and http errors (not auth)
        return kind in {"timeout", "network", "http"}

    def on_retryable_error(self, error: Any) -> bool:
        """Handle a retryable error, incrementing retry count.

        Args:
            error: The retryable error.

        Returns:
            True if retry should proceed, False if max retries exceeded.
        """
        self._retry_count += 1

        if self._retry_count >= self._max_retries:
            if self.on_max_retries is not None:
                self.on_max_retries(to_error(error))
            return False

        if self.on_retry is not None:
            self.on_retry(to_error(error))

        return True

    def _classify_error(self, error: Exception) -> dict[str, Any]:
        """Classify an error for logging and debugging.

        Args:
            error: The error to classify.

        Returns:
            A dict with classification details.
        """
        classification: dict[str, Any] = {
            "name": error.__class__.__name__,
            "message": error_message(error),
        }

        # Add errno info for filesystem errors
        code = get_errno_code(error)
        if code is not None:
            classification["errno_code"] = code
            classification["is_fs_inaccessible"] = is_fs_inaccessible(error)

        # Add path info for ENOENT errors
        path = get_errno_path(error)
        if path is not None:
            classification["errno_path"] = path

        return classification

    def is_auth_error(self, error: Any) -> bool:
        """Check if an error is an authentication error.

        Args:
            error: The error to check.

        Returns:
            True if this is an auth error.
        """
        return classify_axios_error(error)["kind"] == "auth"

    def is_network_error(self, error: Any) -> bool:
        """Check if an error is a network error.

        Args:
            error: The error to check.

        Returns:
            True if this is a network error.
        """
        return classify_axios_error(error)["kind"] == "network"

    def is_timeout_error(self, error: Any) -> bool:
        """Check if an error is a timeout error.

        Args:
            error: The error to check.

        Returns:
            True if this is a timeout error.
        """
        return classify_axios_error(error)["kind"] == "timeout"

    def get_compact_error(self, error: Any) -> str:
        """Get a compact error representation suitable for tool results.

        Args:
            error: The error to format.

        Returns:
            A compact error String with limited stack frames.
        """
        return short_error_stack(error, max_frames=3)


# =============================================================================
# Error Recovery Strategies
# =============================================================================


class ErrorAction(Enum):
    """Error recovery actions.

    Determines what action the QueryEngine should take after an error occurs.
    """

    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_MODEL = "fallback_model"
    RECOVER_OUTPUT = "recover_output"
    MARK_FAILED = "mark_failed"
    ASK_USER = "ask_user"


@dataclass
class ErrorRecoveryConfig:
    """Configuration for error recovery behavior.

    Attributes:
        max_retries: Maximum number of retries per task.
        base_backoff_seconds: Base delay for exponential backoff.
        max_backoff_seconds: Maximum delay cap for backoff.
        max_consecutive_529_errors: Max consecutive 529 (overloaded) errors
            before triggering model fallback.
        max_output_tokens_recovery_limit: Max times to attempt recovery from
            partial output after hitting max_output_tokens.
    """

    max_retries: int = 10
    base_backoff_seconds: float = 0.5
    max_backoff_seconds: float = 60.0
    max_consecutive_529_errors: int = 3
    max_output_tokens_recovery_limit: int = 3

    # Consecutive 529 error counter (not exposed as a public field)
    _consecutive_529_errors: int = field(default=0, repr=False)


def _get_retry_delay(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 60.0,
) -> float:
    """Calculate delay for retry with exponential backoff and jitter.

    Args:
        attempt: The current retry attempt number (1-indexed).
        base_delay: Base delay in seconds.
        max_delay: Maximum delay cap in seconds.

    Returns:
        Delay in seconds with jitter applied.
    """
    import math

    delay = min(base_delay * math.pow(2, attempt - 1), max_delay)
    jitter = random.random() * 0.25 * delay
    return delay + jitter


def _is_retryable_error(error: Any) -> bool:
    """Check if an error is retryable by type or message.

    Args:
        error: The error to check.

    Returns:
        True if the error is retryable.
    """
    retryable_types: tuple[type, ...] = (
        TimeoutError,
        ConnectionError,
    )

    error_msg = error_message(error).lower()
    retryable_keywords = (
        "timeout",
        "connection",
        "network",
        "rate limit",
        "429",
        "500",
        "502",
        "503",
        "529",
        "overloaded",
    )

    return (
        isinstance(error, retryable_types)
        or any(kw in error_msg for kw in retryable_keywords)
    )


def _is_api_error(error: Any) -> bool:
    """Check if an error is an API-related error.

    Args:
        error: The error to check.

    Returns:
        True if the error appears to be API-related.
    """
    error_msg = error_message(error).lower()
    api_keywords = (
        "auth",
        "api",
        "401",
        "403",
        "429",
        "500",
        "502",
        "503",
        "rate limit",
    )
    return any(kw in error_msg for kw in api_keywords)


def _is_rate_limit_error(error: Any) -> bool:
    """Check if an error is a rate limit (429) error.

    Args:
        error: The error to check.

    Returns:
        True if the error is a rate limit error.
    """
    return "429" in error_message(error) or "rate limit" in error_message(error).lower()


def _is_server_overload_error(error: Any) -> bool:
    """Check if an error is a server overload (529) error.

    Args:
        error: The error to check.

    Returns:
        True if the error is a server overload error.
    """
    error_msg = error_message(error).lower()
    return "529" in error_msg or "overloaded" in error_msg


def _has_meaningful_output(output: str) -> bool:
    """Check if partial output is meaningful enough to recover.

    Args:
        output: The partial output string.

    Returns:
        True if the output is substantial enough for recovery.
    """
    return len(output.strip()) > 50


# =============================================================================
# Extended Query Error Handler with Strategy Support
# =============================================================================


class ExtendedQueryErrorHandler(QueryErrorHandler):
    """Extended error handler supporting 6 recovery strategies.

    Inherits from QueryErrorHandler and adds strategy-based error recovery
    with ErrorAction determination.

    Additional Attributes:
        config: ErrorRecoveryConfig instance.
        _retry_counters: Per-task retry counters.
        _partial_outputs: Per-task partial output storage.
        _consecutive_529_count: Count of consecutive 529 errors.
        on_action: Callback invoked with determined ErrorAction.
        on_fallback: Callback invoked when fallback model is triggered.
        on_recover_output: Callback invoked when partial output is recovered.
    """

    def __init__(
        self,
        config: ErrorRecoveryConfig | None = None,
        on_error: ErrorHandlerCallback | None = None,
        on_abort: AbortCallback | None = None,
        on_retry: ErrorHandlerCallback | None = None,
        on_max_retries: ErrorHandlerCallback | None = None,
        on_action: Callable[[ErrorAction, Any], None] | None = None,
        on_fallback: Callable[[str, str], None] | None = None,
        on_recover_output: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the extended error handler.

        Args:
            config: Error recovery configuration.
            on_error: Called for each non-abort error.
            on_abort: Called when an operation is aborted.
            on_retry: Called before retrying after a retryable error.
            on_max_retries: Called when maximum retries is exceeded.
            on_action: Called with the determined ErrorAction and error.
            on_fallback: Called when fallback model is triggered (original, fallback).
            on_recover_output: Called when partial output is recovered (task_id).
        """
        super().__init__(
            on_error=on_error,
            on_abort=on_abort,
            on_retry=on_retry,
            on_max_retries=on_max_retries,
        )
        self.config = config or ErrorRecoveryConfig()
        self._retry_counters: dict[str, int] = {}
        self._partial_outputs: dict[str, str] = {}
        self._consecutive_529_count = 0
        self.on_action = on_action
        self.on_fallback = on_fallback
        self.on_recover_output = on_recover_output

    def determine_action(
        self,
        error: Any,
        context: dict[str, Any] | None = None,
    ) -> ErrorAction:
        """Determine the appropriate recovery action for an error.

        Flow:
        1. Check if error is retryable → ASK_USER if not
        2. Check retry budget → ASK_USER if exhausted
        3. Check for 529 consecutive errors → FALLBACK_MODEL if exhausted
        4. Check for partial output recovery → RECOVER_OUTPUT if available
        5. Check if rate limit error → RETRY_WITH_BACKOFF
        6. Check if server overload (529) → RETRY or FALLBACK_MODEL
        7. Default → RETRY_WITH_BACKOFF

        Args:
            error: The error to evaluate.
            context: Optional context dict with 'task_id', 'model', etc.

        Returns:
            The determined ErrorAction.
        """
        ctx = context or {}
        task_id = ctx.get("task_id", "")
        err = to_error(error)

        # Call on_abort for abort errors (preserving base behavior)
        if is_abort_error(err):
            if self.on_abort is not None:
                self.on_abort()
            action = ErrorAction.ASK_USER
            self._notify_action(action, err)
            return action

        # Call on_error only for non-retryable errors (ASK_USER case)
        # Retryable errors go through the strategy flow without on_error

        # 1. Non-retryable errors → ask user
        if not _is_retryable_error(err):
            action = ErrorAction.ASK_USER
            if self.on_error is not None:
                self.on_error(err)
            self._notify_action(action, err)
            return action

        # Track consecutive 529 errors
        if _is_server_overload_error(err):
            self._consecutive_529_count += 1
        else:
            self._consecutive_529_count = 0

        # 2. Check retry budget
        retry_count = self._retry_counters.get(task_id, 0)
        if retry_count >= self.config.max_retries:
            action = ErrorAction.ASK_USER
            self._notify_action(action, err)
            return action

        # 3. Check for max consecutive 529 → fallback model
        if self._consecutive_529_count >= self.config.max_consecutive_529_errors:
            model = ctx.get("model", "")
            fallback_model = ctx.get("fallback_model", "")
            if fallback_model:
                action = ErrorAction.FALLBACK_MODEL
                self._notify_action(action, err)
                self._notify_fallback(model, fallback_model)
                return action
            # No fallback model available → mark failed
            action = ErrorAction.MARK_FAILED
            if self.on_error is not None:
                self.on_error(err)
            self._notify_action(action, err)
            return action

        # 4. Partial output recovery
        if task_id:
            partial = self._partial_outputs.get(task_id)
            if partial and _has_meaningful_output(partial):
                action = ErrorAction.RECOVER_OUTPUT
                self._notify_action(action, err)
                self._notify_recover_output(task_id)
                self.clear_partial_output(task_id)
                return action

        # 5. Rate limit errors → retry with backoff
        if _is_rate_limit_error(err):
            self._retry_counters[task_id] = retry_count + 1
            action = ErrorAction.RETRY_WITH_BACKOFF
            self._notify_action(action, err)
            return action

        # 6. 529 errors → retry (may fallback on next 529)
        if _is_server_overload_error(err):
            self._retry_counters[task_id] = retry_count + 1
            action = ErrorAction.RETRY
            self._notify_action(action, err)
            return action

        # 7. Timeout/Connection errors → simple retry
        # These are retryable but don't need backoff
        self._retry_counters[task_id] = retry_count + 1
        action = ErrorAction.RETRY
        self._notify_action(action, err)
        return action

    def get_retry_delay(self, attempt: int | None = None) -> float:
        """Calculate backoff delay for the given attempt.

        Args:
            attempt: Retry attempt number. Defaults to current retry_count + 1.

        Returns:
            Delay in seconds with exponential backoff and jitter.
        """
        if attempt is None:
            attempt = self._retry_count + 1
        return _get_retry_delay(
            attempt,
            self.config.base_backoff_seconds,
            self.config.max_backoff_seconds,
        )

    def save_partial_output(self, task_id: str, output: str) -> None:
        """Save partial output for potential recovery.

        Args:
            task_id: Unique identifier for the task.
            output: The partial output string to save.
        """
        self._partial_outputs[task_id] = output

    def clear_partial_output(self, task_id: str) -> None:
        """Clear saved partial output after successful recovery.

        Args:
            task_id: Unique identifier for the task.
        """
        self._partial_outputs.pop(task_id, None)

    def get_retry_count(self, task_id: str) -> int:
        """Get the retry count for a specific task.

        Args:
            task_id: Unique identifier for the task.

        Returns:
            Number of retries attempted for this task.
        """
        return self._retry_counters.get(task_id, 0)

    def reset_task(self, task_id: str) -> None:
        """Reset state for a specific task.

        Args:
            task_id: Unique identifier for the task.
        """
        self._retry_counters.pop(task_id, None)
        self._partial_outputs.pop(task_id, None)

    def reset_all(self) -> None:
        """Reset all error handler state."""
        self._retry_counters.clear()
        self._partial_outputs.clear()
        self._consecutive_529_count = 0
        self.reset()

    def _notify_action(self, action: ErrorAction, error: Exception) -> None:
        """Invoke on_action callback if registered."""
        if self.on_action is not None:
            self.on_action(action, error)

    def _notify_fallback(self, original_model: str, fallback_model: str) -> None:
        """Invoke on_fallback callback if registered."""
        if self.on_fallback is not None:
            self.on_fallback(original_model, fallback_model)

    def _notify_recover_output(self, task_id: str) -> None:
        """Invoke on_recover_output callback if registered."""
        if self.on_recover_output is not None:
            self.on_recover_output(task_id)
