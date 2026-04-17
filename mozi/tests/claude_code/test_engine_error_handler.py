"""Tests for engine/error_handler.py."""

from __future__ import annotations

from typing import Any

from claude_code.engine.error_handler import (
    AbortError,
    ClaudeError,
    ConfigParseError,
    ErrorAction,
    ErrorRecoveryConfig,
    ExtendedQueryErrorHandler,
    MalformedCommandError,
    QueryErrorHandler,
    ShellError,
    TelemetrySafeError,
    TeleportOperationError,
    _get_retry_delay,
    _has_meaningful_output,
    _is_api_error,
    _is_rate_limit_error,
    _is_retryable_error,
    _is_server_overload_error,
    classify_axios_error,
    error_message,
    get_errno_code,
    get_errno_path,
    has_exact_error_message,
    is_abort_error,
    is_enoent,
    is_fs_inaccessible,
    short_error_stack,
    to_error,
)


class TestErrorClasses:
    def test_claude_error(self) -> None:
        """ClaudeError should be a basic exception."""
        err = ClaudeError("Something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "Something went wrong"

    def test_malformed_command_error(self) -> None:
        """MalformedCommandError should be a basic exception."""
        err = MalformedCommandError("Bad command")
        assert isinstance(err, Exception)
        assert str(err) == "Bad command"

    def test_abort_error(self) -> None:
        """AbortError should have correct name."""
        err = AbortError()
        assert err.name == "AbortError"
        assert str(err) == ""

        err2 = AbortError("Operation cancelled")
        assert str(err2) == "Operation cancelled"

    def test_config_parse_error(self) -> None:
        """ConfigParseError should have filePath and defaultConfig."""
        err = ConfigParseError("Invalid JSON", "/path/config.json", {})
        assert err.name == "ConfigParseError"
        assert err.file_path == "/path/config.json"
        assert err.default_config == {}

    def test_shell_error(self) -> None:
        """ShellError should hold stdout, stderr, code, interrupted."""
        err = ShellError(stdout="ok", stderr="error", code=1, interrupted=False)
        assert err.stdout == "ok"
        assert err.stderr == "error"
        assert err.code == 1
        assert err.interrupted is False
        assert "failed" in str(err)
        assert "exit 1" in str(err)

    def test_teleport_operation_error(self) -> None:
        """TeleportOperationError should have formattedMessage."""
        err = TeleportOperationError("Failed", "formatted msg")
        assert err.name == "TeleportOperationError"
        assert err.formatted_message == "formatted msg"

    def test_telemetry_safe_error(self) -> None:
        """TelemetrySafeError should store both messages."""
        err = TelemetrySafeError("Full message with path /tmp", "Safe message")
        assert err.name == "TelemetrySafeError"
        assert err.telemetry_message == "Safe message"

        err2 = TelemetrySafeError("Same message")
        assert err2.telemetry_message == "Same message"


class TestErrorUtilities:
    def test_is_abort_error_abort_error_instance(self) -> None:
        """is_abort_error should match AbortError instances."""
        assert is_abort_error(AbortError())
        assert is_abort_error(AbortError("cancelled"))

    def test_is_abort_error_none(self) -> None:
        """is_abort_error should return False for None."""
        assert not is_abort_error(None)

    def test_is_abort_error_other(self) -> None:
        """is_abort_error should return False for other errors."""
        assert not is_abort_error(ValueError("test"))
        assert not is_abort_error(RuntimeError("test"))

    def test_has_exact_error_message(self) -> None:
        """has_exact_error_message should match exact messages."""
        err = ValueError("exact match")
        assert has_exact_error_message(err, "exact match")
        assert not has_exact_error_message(err, "different")

    def test_has_exact_error_message_none(self) -> None:
        """has_exact_error_message should return False for None."""
        assert not has_exact_error_message(None, "msg")

    def test_to_error_exception(self) -> None:
        """to_error should return exceptions unchanged."""
        err = ValueError("test")
        assert to_error(err) is err

    def test_to_error_non_exception(self) -> None:
        """to_error should wrap non-exceptions."""
        assert isinstance(to_error("string error"), Exception)
        assert isinstance(to_error(42), Exception)

    def test_error_message_exception(self) -> None:
        """error_message should extract from exceptions."""
        assert error_message(ValueError("hello")) == "hello"
        assert error_message(AbortError("stopped")) == "stopped"

    def test_error_message_non_exception(self) -> None:
        """error_message should convert non-exceptions to strings."""
        assert error_message("plain string") == "plain string"
        assert error_message(42) == "42"

    def test_get_errno_code_present(self) -> None:
        """get_errno_code should extract code from errors."""

        class FakeError(Exception):
            code = "ENOENT"

        assert get_errno_code(FakeError()) == "ENOENT"

    def test_get_errno_code_none(self) -> None:
        """get_errno_code should return None when no code."""
        assert get_errno_code(ValueError("test")) is None
        assert get_errno_code(None) is None

    def test_is_enoent(self) -> None:

        class FakeENOENT(Exception):
            code = "ENOENT"

        assert is_enoent(FakeENOENT())
        assert not is_enoent(ValueError("test"))

    def test_get_errno_path(self) -> None:

        class FakeError(Exception):
            path = "/tmp/file.txt"

        assert get_errno_path(FakeError()) == "/tmp/file.txt"
        assert get_errno_path(ValueError("test")) is None

    def test_short_error_stack_exception(self) -> None:
        """short_error_stack should format with limited frames."""
        try:
            raise ValueError("test error")
        except ValueError as e:
            result = short_error_stack(e, max_frames=3)
            assert "test error" in result

    def test_short_error_stack_non_exception(self) -> None:
        """short_error_stack should convert non-exceptions."""
        assert short_error_stack("just a string") == "just a string"
        assert short_error_stack(123) == "123"

    def test_is_fs_inaccessible(self) -> None:
        """is_fs_inaccessible should match filesystem access errors."""

        class FakeError(Exception):
            code = "EACCES"

        assert is_fs_inaccessible(FakeError())
        assert not is_fs_inaccessible(ValueError("test"))


class TestClassifyAxiosError:
    def test_non_axios_error(self) -> None:
        """Non-axios errors should be classified as 'other'."""
        result = classify_axios_error(ValueError("test"))
        assert result["kind"] == "other"
        assert result["message"] == "test"

    def test_none(self) -> None:
        """None should be classified as 'other'."""
        result = classify_axios_error(None)
        assert result["kind"] == "other"

    def test_auth_error(self) -> None:

        class FakeAuthError(Exception):
            is_axios_error = True

            @property
            def response(self) -> dict:  # type: ignore[type-arg]
                return {"status": 401}  # type: ignore[return-value]

        result = classify_axios_error(FakeAuthError())
        assert result["kind"] == "auth"
        assert result["status"] == 401

    def test_timeout_error(self) -> None:

        class FakeTimeoutError(Exception):
            is_axios_error = True
            code = "ECONNABORTED"

            @property
            def response(self) -> None:
                return None

        result = classify_axios_error(FakeTimeoutError())
        assert result["kind"] == "timeout"

    def test_network_error(self) -> None:

        class FakeNetError(Exception):
            is_axios_error = True
            code = "ECONNREFUSED"

            @property
            def response(self) -> None:
                return None

        result = classify_axios_error(FakeNetError())
        assert result["kind"] == "network"


class TestQueryErrorHandler:
    def test_default_initialization(self) -> None:
        """QueryErrorHandler should initialize with defaults."""
        handler = QueryErrorHandler()
        assert handler.retry_count == 0
        assert handler.max_retries == 3

    def test_callback_initialization(self) -> None:
        """QueryErrorHandler should accept callback arguments."""
        errors: list[Exception] = []

        def on_error(e: Exception) -> None:
            errors.append(e)

        def on_abort() -> None:
            errors.append(Exception("aborted"))

        handler = QueryErrorHandler(on_error=on_error, on_abort=on_abort)
        assert handler.on_error is on_error
        assert handler.on_abort is on_abort

    def test_handle_error_calls_on_error(self) -> None:
        """handle_error should call on_error for non-abort errors."""
        errors: list[Exception] = []
        handler = QueryErrorHandler(on_error=errors.append)
        handler.handle_error(ValueError("test"))
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    def test_handle_error_calls_on_abort(self) -> None:
        """handle_error should call on_abort for abort errors."""
        aborted = False

        def on_abort() -> None:
            nonlocal aborted
            aborted = True

        handler = QueryErrorHandler(on_abort=on_abort)
        handler.handle_error(AbortError())
        assert aborted

    def test_handle_error_non_exception(self) -> None:
        """handle_error should wrap non-exception values."""
        errors: list[Exception] = []
        handler = QueryErrorHandler(on_error=errors.append)
        handler.handle_error("string error")
        assert len(errors) == 1
        assert isinstance(errors[0], Exception)

    def test_should_retry_retryable(self) -> None:

        class FakeTimeoutError(Exception):
            is_axios_error = True
            code = "ECONNABORTED"

            @property
            def response(self) -> None:
                return None

        handler = QueryErrorHandler()
        assert handler.should_retry(FakeTimeoutError())

    def test_should_retry_auth_error(self) -> None:

        class FakeAuthError(Exception):
            is_axios_error = True

            @property
            def response(self) -> dict:  # type: ignore[type-arg]
                return {"status": 401}  # type: ignore[return-value]

        handler = QueryErrorHandler()
        assert not handler.should_retry(FakeAuthError())

    def test_should_retry_max_retries_exceeded(self) -> None:

        class FakeTimeoutError(Exception):
            is_axios_error = True
            code = "ECONNABORTED"

            @property
            def response(self) -> None:
                return None

        handler = QueryErrorHandler()
        handler._retry_count = 3
        assert not handler.should_retry(FakeTimeoutError())

    def test_on_retryable_error_increments_count(self) -> None:
        """on_retryable_error should increment retry count."""
        handler = QueryErrorHandler()
        assert handler.retry_count == 0
        handler.on_retryable_error(ValueError("test"))
        assert handler.retry_count == 1

    def test_on_retryable_error_calls_callback(self) -> None:
        """on_retryable_error should call on_retry callback."""
        called = False

        def on_retry(_e: Exception) -> None:
            nonlocal called
            called = True

        handler = QueryErrorHandler(on_retry=on_retry)
        handler.on_retryable_error(ValueError("test"))
        assert called

    def test_on_retryable_error_max_retries(self) -> None:
        """on_retryable_error should call on_max_retries at limit."""
        called = False

        def on_max_retries(_e: Exception) -> None:
            nonlocal called
            called = True

        handler = QueryErrorHandler(on_max_retries=on_max_retries)
        handler._retry_count = 2
        result = handler.on_retryable_error(ValueError("test"))
        assert called
        assert result is False

    def test_reset(self) -> None:
        """reset should clear retry counter."""
        handler = QueryErrorHandler()
        handler._retry_count = 5
        handler.reset()
        assert handler.retry_count == 0

    def test_max_retries_setter(self) -> None:
        """max_retries setter should update and validate."""
        handler = QueryErrorHandler()
        handler.max_retries = 10
        assert handler.max_retries == 10
        handler.max_retries = -1
        assert handler.max_retries == 0

    def test_is_auth_error(self) -> None:

        class FakeAuthError(Exception):
            is_axios_error = True

            @property
            def response(self) -> dict:  # type: ignore[type-arg]
                return {"status": 403}  # type: ignore[return-value]

        handler = QueryErrorHandler()
        assert handler.is_auth_error(FakeAuthError())
        assert not handler.is_auth_error(ValueError("test"))

    def test_is_network_error(self) -> None:

        class FakeNetError(Exception):
            is_axios_error = True
            code = "ENOTFOUND"

            @property
            def response(self) -> None:
                return None

        handler = QueryErrorHandler()
        assert handler.is_network_error(FakeNetError())

    def test_is_timeout_error(self) -> None:

        class FakeTimeoutError(Exception):
            is_axios_error = True
            code = "ECONNABORTED"

            @property
            def response(self) -> None:
                return None

        handler = QueryErrorHandler()
        assert handler.is_timeout_error(FakeTimeoutError())

    def test_get_compact_error(self) -> None:
        """get_compact_error should produce limited-stack output."""
        try:
            raise ValueError("compact test")
        except ValueError as e:
            result = QueryErrorHandler().get_compact_error(e)
            assert "compact test" in result

    def test_classify_error_includes_fs_info(self) -> None:
        """_classify_error should include filesystem error details."""

        class FakeError(Exception):
            code = "ENOENT"

            @property
            def path(self) -> str:
                return "/missing/file.txt"

        handler = QueryErrorHandler()
        classified = handler._classify_error(FakeError())
        assert classified["name"] == "FakeError"
        assert classified["errno_code"] == "ENOENT"
        assert classified["is_fs_inaccessible"] is True
        assert classified["errno_path"] == "/missing/file.txt"


class TestErrorAction:
    def test_error_action_values(self) -> None:
        """ErrorAction enum should have all 6 expected values."""
        assert ErrorAction.RETRY.value == "retry"
        assert ErrorAction.RETRY_WITH_BACKOFF.value == "retry_with_backoff"
        assert ErrorAction.FALLBACK_MODEL.value == "fallback_model"
        assert ErrorAction.RECOVER_OUTPUT.value == "recover_output"
        assert ErrorAction.MARK_FAILED.value == "mark_failed"
        assert ErrorAction.ASK_USER.value == "ask_user"

    def test_error_action_count(self) -> None:
        """ErrorAction should have exactly 6 members."""
        assert len(ErrorAction) == 6


class TestErrorRecoveryConfig:
    def test_default_values(self) -> None:
        """ErrorRecoveryConfig should have sensible defaults."""
        config = ErrorRecoveryConfig()
        assert config.max_retries == 10
        assert config.base_backoff_seconds == 0.5
        assert config.max_backoff_seconds == 60.0
        assert config.max_consecutive_529_errors == 3
        assert config.max_output_tokens_recovery_limit == 3

    def test_custom_values(self) -> None:
        """ErrorRecoveryConfig should accept custom values."""
        config = ErrorRecoveryConfig(
            max_retries=5,
            base_backoff_seconds=1.0,
            max_backoff_seconds=30.0,
            max_consecutive_529_errors=2,
        )
        assert config.max_retries == 5
        assert config.base_backoff_seconds == 1.0
        assert config.max_backoff_seconds == 30.0
        assert config.max_consecutive_529_errors == 2


class TestErrorRecoveryHelpers:
    def test_is_retryable_timeout_error(self) -> None:
        """Timeout errors should be retryable."""
        assert _is_retryable_error(TimeoutError("timed out"))

    def test_is_retryable_connection_error(self) -> None:
        """Connection errors should be retryable."""
        assert _is_retryable_error(ConnectionError("connection refused"))

    def test_is_retryable_429_error(self) -> None:
        """Rate limit errors should be retryable."""
        assert _is_retryable_error(Exception("rate limit exceeded (429)"))

    def test_is_retryable_529_error(self) -> None:
        """Server overload errors should be retryable."""
        assert _is_retryable_error(Exception("server overloaded (529)"))

    def test_is_retryable_500_error(self) -> None:
        """Internal server errors should be retryable."""
        assert _is_retryable_error(Exception("internal server error (500)"))

    def test_is_retryable_network_keyword(self) -> None:
        """Network-related errors should be retryable."""
        assert _is_retryable_error(Exception("network connection failed"))

    def test_not_retryable_value_error(self) -> None:
        """ValueError should not be retryable."""
        assert not _is_retryable_error(ValueError("invalid value"))

    def test_not_retryable_key_error(self) -> None:
        """KeyError should not be retryable."""
        assert not _is_retryable_error(KeyError("missing_key"))

    def test_is_api_error_auth(self) -> None:
        """Auth errors should be identified as API errors."""
        assert _is_api_error(Exception("authentication failed (401)"))
        assert _is_api_error(Exception("auth error"))

    def test_is_api_error_rate_limit(self) -> None:
        """Rate limit errors should be identified as API errors."""
        assert _is_api_error(Exception("rate limit exceeded"))

    def test_is_api_error_5xx(self) -> None:
        """5xx errors should be identified as API errors."""
        assert _is_api_error(Exception("internal server error (500)"))

    def test_not_api_error(self) -> None:
        """Non-API errors should not be identified as API errors."""
        assert not _is_api_error(ValueError("invalid value"))

    def test_is_rate_limit_error_429(self) -> None:
        """Errors with 429 should be rate limit errors."""
        assert _is_rate_limit_error(Exception("rate limit exceeded (429)"))

    def test_is_rate_limit_error_keywords(self) -> None:
        """Rate limit keywords should be detected."""
        assert _is_rate_limit_error(Exception("rate limit exceeded"))

    def test_not_rate_limit_error(self) -> None:
        """Non-rate-limit errors should not be detected."""
        assert not _is_rate_limit_error(Exception("timeout (408)"))

    def test_is_server_overload_error_529(self) -> None:
        """Errors with 529 should be server overload errors."""
        assert _is_server_overload_error(Exception("server overloaded (529)"))

    def test_is_server_overload_error_message(self) -> None:
        """Overloaded keyword should be detected."""
        assert _is_server_overload_error(Exception("service overloaded"))

    def test_not_server_overload_error(self) -> None:
        """Non-overload errors should not be detected."""
        assert not _is_server_overload_error(Exception("timeout"))

    def test_has_meaningful_output_true(self) -> None:
        """Strings longer than 50 chars should be meaningful."""
        assert _has_meaningful_output("x" * 51)

    def test_has_meaningful_output_exactly_50(self) -> None:
        """Exactly 50 chars should not be meaningful."""
        assert not _has_meaningful_output("x" * 50)

    def test_has_meaningful_output_whitespace(self) -> None:
        """Whitespace-only strings should not be meaningful."""
        assert not _has_meaningful_output("   ")

    def test_retry_delay_exponential(self) -> None:
        """Retry delay should increase exponentially."""
        d1 = _get_retry_delay(1)
        d2 = _get_retry_delay(2)
        d3 = _get_retry_delay(3)
        # Each delay should be roughly double the previous
        assert d2 > d1
        assert d3 > d2

    def test_retry_delay_respects_max(self) -> None:
        """Retry delay should be capped at max_delay."""
        d = _get_retry_delay(100, max_delay=5.0)
        assert d <= 5.0 * 1.25  # max + jitter

    def test_retry_delay_has_jitter(self) -> None:
        """Retry delay should have some randomness."""
        delays = {_get_retry_delay(1) for _ in range(10)}
        # With jitter, we should get multiple different values
        assert len(delays) > 1


class TestExtendedQueryErrorHandler:
    def test_extended_initialization(self) -> None:
        """ExtendedQueryErrorHandler should initialize with defaults."""
        handler = ExtendedQueryErrorHandler()
        assert handler.config.max_retries == 10
        assert handler.config.max_consecutive_529_errors == 3
        assert handler._retry_counters == {}
        assert handler._partial_outputs == {}
        assert handler._consecutive_529_count == 0

    def test_extended_initialization_with_config(self) -> None:
        """ExtendedQueryErrorHandler should accept custom config."""
        config = ErrorRecoveryConfig(max_retries=5)
        handler = ExtendedQueryErrorHandler(config=config)
        assert handler.config is config
        assert handler.config.max_retries == 5

    def test_extended_initialization_with_callbacks(self) -> None:
        """ExtendedQueryErrorHandler should accept all callbacks."""
        actions: list[ErrorAction] = []
        fallbacks: list[tuple[str, str]] = []
        recovered: list[str] = []

        def on_action(action: ErrorAction, _: Any) -> None:
            actions.append(action)

        def on_fallback(original: str, fallback: str) -> None:
            fallbacks.append((original, fallback))

        def on_recover(task_id: str) -> None:
            recovered.append(task_id)

        handler = ExtendedQueryErrorHandler(
            on_action=on_action,
            on_fallback=on_fallback,
            on_recover_output=on_recover,
        )
        assert handler.on_action is on_action
        assert handler.on_fallback is on_fallback
        assert handler.on_recover_output is on_recover

    def test_determine_action_non_retryable_asks_user(self) -> None:
        """Non-retryable errors should return ASK_USER."""
        handler = ExtendedQueryErrorHandler()
        action = handler.determine_action(ValueError("invalid value"))
        assert action == ErrorAction.ASK_USER

    def test_determine_action_timeout_retries(self) -> None:
        """Timeout errors should return RETRY."""
        handler = ExtendedQueryErrorHandler()
        action = handler.determine_action(TimeoutError("timed out"))
        assert action == ErrorAction.RETRY

    def test_determine_action_rate_limit_retries_with_backoff(self) -> None:
        """Rate limit errors should return RETRY_WITH_BACKOFF."""
        handler = ExtendedQueryErrorHandler()
        action = handler.determine_action(Exception("rate limit (429)"))
        assert action == ErrorAction.RETRY_WITH_BACKOFF

    def test_determine_action_server_overload_retries(self) -> None:
        """529 errors should return RETRY initially."""
        handler = ExtendedQueryErrorHandler()
        action = handler.determine_action(Exception("server overloaded (529)"))
        assert action == ErrorAction.RETRY

    def test_determine_action_max_529_triggers_fallback(self) -> None:
        """Max consecutive 529 errors should trigger FALLBACK_MODEL."""
        config = ErrorRecoveryConfig(max_consecutive_529_errors=2)
        handler = ExtendedQueryErrorHandler(config=config)
        # Trigger first 529
        handler.determine_action(Exception("server overloaded (529)"))
        # Trigger second 529
        handler.determine_action(Exception("server overloaded (529)"))

    def test_determine_action_529_with_fallback_model(self) -> None:
        """Max 529 errors with fallback model should return FALLBACK_MODEL."""
        config = ErrorRecoveryConfig(max_consecutive_529_errors=1)
        handler = ExtendedQueryErrorHandler(config=config)
        action = handler.determine_action(
            Exception("server overloaded (529)"),
            context={"model": "claude-opus-4", "fallback_model": "claude-sonnet-4"},
        )
        assert action == ErrorAction.FALLBACK_MODEL

    def test_determine_action_fallback_callback(self) -> None:
        """Fallback action should invoke on_fallback callback."""
        fallbacks: list[tuple[str, str]] = []

        def on_fallback(original: str, fallback: str) -> None:
            fallbacks.append((original, fallback))

        config = ErrorRecoveryConfig(max_consecutive_529_errors=1)
        handler = ExtendedQueryErrorHandler(config=config, on_fallback=on_fallback)
        handler.determine_action(
            Exception("server overloaded (529)"),
            context={"model": "opus", "fallback_model": "sonnet"},
        )
        assert fallbacks == [("opus", "sonnet")]

    def test_determine_action_no_fallback_available_marks_failed(self) -> None:
        """Max 529 without fallback model should return MARK_FAILED."""
        config = ErrorRecoveryConfig(max_consecutive_529_errors=1)
        handler = ExtendedQueryErrorHandler(config=config)
        action = handler.determine_action(Exception("server overloaded (529)"))
        assert action == ErrorAction.MARK_FAILED

    def test_determine_action_retry_budget_exhausted(self) -> None:
        """Exhausted retry budget should return ASK_USER."""
        config = ErrorRecoveryConfig(max_retries=2)
        handler = ExtendedQueryErrorHandler(config=config)
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        action = handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        assert action == ErrorAction.ASK_USER

    def test_determine_action_partial_output_recovery(self) -> None:
        """Partial output with meaningful content should return RECOVER_OUTPUT."""
        handler = ExtendedQueryErrorHandler()
        handler.save_partial_output("task-1", "x" * 60)
        action = handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        assert action == ErrorAction.RECOVER_OUTPUT

    def test_determine_action_partial_output_short_not_recovered(self) -> None:
        """Short partial output should not trigger RECOVER_OUTPUT."""
        handler = ExtendedQueryErrorHandler()
        handler.save_partial_output("task-1", "short")
        action = handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        # Short output doesn't trigger recovery; falls through to retry
        assert action == ErrorAction.RETRY

    def test_determine_action_action_callback(self) -> None:
        """determine_action should invoke on_action callback."""
        actions: list[ErrorAction] = []

        def on_action(action: ErrorAction, _: Any) -> None:
            actions.append(action)

        handler = ExtendedQueryErrorHandler(on_action=on_action)
        handler.determine_action(TimeoutError("timed out"))
        assert actions == [ErrorAction.RETRY]

    def test_determine_action_recover_output_callback(self) -> None:
        """RECOVER_OUTPUT action should invoke on_recover_output callback."""
        recovered: list[str] = []

        def on_recover(task_id: str) -> None:
            recovered.append(task_id)

        handler = ExtendedQueryErrorHandler(
            on_recover_output=on_recover,
        )
        handler.save_partial_output("task-recover", "x" * 60)
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-recover"},
        )
        assert recovered == ["task-recover"]

    def test_determine_action_clears_partial_after_recovery(self) -> None:
        """Partial output should be cleared after recovery."""
        handler = ExtendedQueryErrorHandler()
        handler.save_partial_output("task-1", "x" * 60)
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        assert "task-1" not in handler._partial_outputs

    def test_get_retry_delay(self) -> None:
        """get_retry_delay should return exponential backoff delay."""
        handler = ExtendedQueryErrorHandler()
        d1 = handler.get_retry_delay(1)
        d2 = handler.get_retry_delay(2)
        assert d2 > d1

    def test_save_partial_output(self) -> None:
        """save_partial_output should store output by task_id."""
        handler = ExtendedQueryErrorHandler()
        handler.save_partial_output("task-1", "some output")
        assert handler._partial_outputs["task-1"] == "some output"

    def test_clear_partial_output(self) -> None:
        """clear_partial_output should remove stored output."""
        handler = ExtendedQueryErrorHandler()
        handler.save_partial_output("task-1", "some output")
        handler.clear_partial_output("task-1")
        assert "task-1" not in handler._partial_outputs

    def test_get_retry_count(self) -> None:
        """get_retry_count should return per-task retry count."""
        handler = ExtendedQueryErrorHandler()
        assert handler.get_retry_count("task-1") == 0
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        assert handler.get_retry_count("task-1") == 1

    def test_reset_task(self) -> None:
        """reset_task should clear state for specific task."""
        handler = ExtendedQueryErrorHandler()
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        handler.save_partial_output("task-1", "output")
        handler.reset_task("task-1")
        assert handler.get_retry_count("task-1") == 0
        assert "task-1" not in handler._partial_outputs

    def test_reset_all(self) -> None:
        """reset_all should clear all state including counters."""
        handler = ExtendedQueryErrorHandler()
        handler.determine_action(
            Exception("server overloaded (529)"),
        )
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        handler.save_partial_output("task-1", "output")
        handler.reset_all()
        assert handler._retry_counters == {}
        assert handler._partial_outputs == {}
        assert handler._consecutive_529_count == 0
        assert handler.retry_count == 0

    def test_extended_inherits_base_callbacks(self) -> None:
        """ExtendedQueryErrorHandler should still support base callbacks."""
        errors: list[Exception] = []
        handler = ExtendedQueryErrorHandler(on_error=errors.append)
        handler.determine_action(ValueError("test"))
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)

    def test_determine_action_abort_error_calls_on_abort(self) -> None:
        """AbortError should call on_abort callback."""
        aborted = False

        def on_abort() -> None:
            nonlocal aborted
            aborted = True

        handler = ExtendedQueryErrorHandler(on_abort=on_abort)
        action = handler.determine_action(AbortError("cancelled"))
        assert aborted
        assert action == ErrorAction.ASK_USER

    def test_determine_action_non_retryable_calls_on_error(self) -> None:
        """Non-retryable errors should call on_error callback."""
        errors: list[Exception] = []
        handler = ExtendedQueryErrorHandler(on_error=errors.append)
        handler.determine_action(KeyError("missing"))
        assert len(errors) == 1
        assert isinstance(errors[0], KeyError)

    def test_extended_reset_increments_retry_count(self) -> None:
        """determine_action should update per-task retry counter."""
        handler = ExtendedQueryErrorHandler()
        assert handler.get_retry_count("task-1") == 0
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        assert handler.get_retry_count("task-1") == 1

    def test_extended_reset_method_clears_base_count(self) -> None:
        """reset() should clear the base _retry_count."""
        handler = ExtendedQueryErrorHandler()
        handler.determine_action(
            TimeoutError("timed out"),
            context={"task_id": "task-1"},
        )
        assert handler.get_retry_count("task-1") == 1
        handler.reset_task("task-1")
        assert handler.get_retry_count("task-1") == 0

