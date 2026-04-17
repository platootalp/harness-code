"""
Tests for engine/error_recovery.py
"""

from __future__ import annotations

import pytest

from claude_code.engine.error_recovery import (
    BASE_DELAY_MS,
    ContextOverflowData,
    DEFAULT_MAX_RETRIES,
    FLOOR_OUTPUT_TOKENS,
    MAX_529_RETRIES,
    CannotRetryError,
    ContextOverflowData,
    FallbackTriggeredError,
    RetryContext,
    RetryOptions,
    calculate_context_overflow_adjustment,
    get_retry_after_ms,
    get_retry_delay,
    is_529_error,
    is_connection_error,
    is_context_overflow_error,
    is_oauth_token_revoked_error,
    is_rate_limit_error,
    is_transient_capacity_error,
    parse_max_tokens_context_overflow_error,
    should_retry,
    should_retry_529,
)


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    def test_default_max_retries(self) -> None:
        assert DEFAULT_MAX_RETRIES == 10

    def test_base_delay(self) -> None:
        assert BASE_DELAY_MS == 500

    def test_floor_output_tokens(self) -> None:
        assert FLOOR_OUTPUT_TOKENS == 3000

    def test_max_529_retries(self) -> None:
        assert MAX_529_RETRIES == 3


# =============================================================================
# CannotRetryError Tests
# =============================================================================


class TestCannotRetryError:
    def test_init(self) -> None:
        original = ValueError("test error")
        context = RetryContext(model="claude-3-5-sonnet")
        err = CannotRetryError(original, context)
        assert str(err) == "test error"
        assert err.name == "CannotRetryError"
        assert err.original_error is original
        assert err.retry_context is context


# =============================================================================
# FallbackTriggeredError Tests
# =============================================================================


class TestFallbackTriggeredError:
    def test_init(self) -> None:
        err = FallbackTriggeredError("opus-4", "sonnet-4")
        assert str(err) == "Model fallback triggered: opus-4 -> sonnet-4"
        assert err.name == "FallbackTriggeredError"
        assert err.original_model == "opus-4"
        assert err.fallback_model == "sonnet-4"


# =============================================================================
# RetryContext Tests
# =============================================================================


class TestRetryContext:
    def test_create_basic(self) -> None:
        ctx = RetryContext(model="claude-3-5-sonnet")
        assert ctx.model == "claude-3-5-sonnet"
        assert ctx.max_tokens_override is None
        assert ctx.thinking_config == {}

    def test_create_with_options(self) -> None:
        ctx = RetryContext(
            model="claude-3-5-sonnet",
            max_tokens_override=1000,
            thinking_config={"type": "enabled", "budget_tokens": 10000},
            fast_mode=True,
        )
        assert ctx.max_tokens_override == 1000
        assert ctx.thinking_config["type"] == "enabled"
        assert ctx.fast_mode is True


# =============================================================================
# RetryOptions Tests
# =============================================================================


class TestRetryOptions:
    def test_create_basic(self) -> None:
        opts = RetryOptions(model="claude-3-5-sonnet")
        assert opts.model == "claude-3-5-sonnet"
        assert opts.max_retries is None
        assert opts.fallback_model is None
        assert opts.query_source is None

    def test_create_with_all_options(self) -> None:
        opts = RetryOptions(
            model="claude-3-5-opus",
            max_retries=5,
            fallback_model="claude-3-5-sonnet",
            thinking_config={"type": "enabled"},
            fast_mode=True,
            query_source="repl_main_thread",
            initial_consecutive_529_errors=2,
        )
        assert opts.max_retries == 5
        assert opts.fallback_model == "claude-3-5-sonnet"
        assert opts.fast_mode is True
        assert opts.query_source == "repl_main_thread"
        assert opts.initial_consecutive_529_errors == 2


# =============================================================================
# Should Retry 529 Tests
# =============================================================================


class TestShouldRetry529:
    def test_none_source_retries(self) -> None:
        """undefined/None query source should retry (conservative)."""
        assert should_retry_529(None) is True

    def test_foreground_sources_retry(self) -> None:
        """Foreground sources should retry on 529."""
        assert should_retry_529("repl_main_thread") is True
        assert should_retry_529("sdk") is True
        assert should_retry_529("compact") is True
        assert should_retry_529("agent:custom") is True

    def test_background_sources_do_not_retry(self) -> None:
        """Background sources should not retry on 529."""
        assert should_retry_529("background") is False
        assert should_retry_529("cron") is False
        assert should_retry_529("summary") is False


# =============================================================================
# Error Classification Tests
# =============================================================================


class TestIs529Error:
    def test_529_status(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Overloaded", status=529)
        assert is_529_error(err) is True

    def test_overloaded_in_message(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError('{"type":"overloaded_error"}', status=200)
        assert is_529_error(err) is True

    def test_not_529(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Bad request", status=400)
        assert is_529_error(err) is False


class TestIsRateLimitError:
    def test_429_status(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Rate limited", status=429)
        assert is_rate_limit_error(err) is True

    def test_not_rate_limit(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Bad request", status=400)
        assert is_rate_limit_error(err) is False


class TestIsTransientCapacityError:
    def test_529(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Overloaded", status=529)
        assert is_transient_capacity_error(err) is True

    def test_429(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Rate limited", status=429)
        assert is_transient_capacity_error(err) is True

    def test_not_transient(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Bad request", status=400)
        assert is_transient_capacity_error(err) is False


class TestIsConnectionError:
    def test_connection_error(self) -> None:
        err = Exception("Connection refused")
        assert is_connection_error(err) is True

    def test_timeout_error(self) -> None:
        err = Exception("Connection timeout")
        assert is_connection_error(err) is True

    def test_econnreset(self) -> None:
        err = Exception("ECONNRESET")
        assert is_connection_error(err) is True

    def test_not_connection_error(self) -> None:
        err = Exception("File not found")
        assert is_connection_error(err) is False


class TestIsOAuthTokenRevokedError:
    def test_oauth_revoked(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("OAuth token has been revoked", status=403)
        assert is_oauth_token_revoked_error(err) is True

    def test_not_oauth(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Forbidden", status=403)
        assert is_oauth_token_revoked_error(err) is False


# =============================================================================
# Context Overflow Tests
# =============================================================================


class TestParseContextOverflowError:
    def test_parse_valid_error(self) -> None:
        from claude_code.services.api.errors import APIError
        msg = "input length and `max_tokens` exceed context limit: 188059 + 20000 > 200000"
        err = APIError(msg, status=400)
        result = parse_max_tokens_context_overflow_error(err)
        assert result is not None
        assert result.input_tokens == 188059
        assert result.max_tokens == 20000
        assert result.context_limit == 200000

    def test_parse_not_overflow(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Bad request", status=400)
        assert parse_max_tokens_context_overflow_error(err) is None

    def test_parse_wrong_status(self) -> None:
        from claude_code.services.api.errors import APIError
        msg = "input length and `max_tokens` exceed context limit: 100 + 100 > 200"
        err = APIError(msg, status=500)
        assert parse_max_tokens_context_overflow_error(err) is None


class TestCalculateContextOverflowAdjustment:
    def test_basic_calculation(self) -> None:
        overflow = ContextOverflowData(
            input_tokens=180000,
            max_tokens=20000,
            context_limit=200000,
        )
        result = calculate_context_overflow_adjustment(overflow, {})
        # available = 200000 - 180000 - 1000 = 19000
        # max(3000, 19000, 1) = 19000
        assert result == 19000

    def test_floor_enforced(self) -> None:
        overflow = ContextOverflowData(
            input_tokens=195000,
            max_tokens=20000,
            context_limit=200000,
        )
        result = calculate_context_overflow_adjustment(overflow, {})
        # available = 200000 - 195000 - 1000 = 4000
        # max(3000, 4000, 1) = 4000
        assert result == 4000

    def test_with_thinking_config(self) -> None:
        overflow = ContextOverflowData(
            input_tokens=180000,
            max_tokens=20000,
            context_limit=200000,
        )
        thinking_config = {"type": "enabled", "budget_tokens": 10000}
        result = calculate_context_overflow_adjustment(overflow, thinking_config)
        # min_required = 10000 + 1 = 10001
        # max(3000, 19000, 10001) = 19000
        assert result == 19000


# =============================================================================
# Retry Delay Tests
# =============================================================================


class TestGetRetryDelay:
    def test_exponential_backoff(self) -> None:
        """Delay should increase exponentially with attempt number (with jitter)."""
        delay1 = get_retry_delay(1)
        delay2 = get_retry_delay(2)
        delay3 = get_retry_delay(3)

        # Each delay should be roughly 2x the previous (with jitter)
        # Base: 500, 1000, 2000, jitter adds up to 25%
        assert 500 <= delay1 <= 625  # 500 * 1.25 = 625
        assert 1000 <= delay2 <= 1250  # 1000 * 1.25 = 1250
        assert 2000 <= delay3 <= 2500  # 2000 * 1.25 = 2500

    def test_respects_max_delay(self) -> None:
        """Delay should be capped at max_delay_ms (including jitter)."""
        delay = get_retry_delay(10, max_delay_ms=1000)
        # 500 * 2^9 = 256000, but capped at 1000
        assert delay <= 1000

    def test_jitter_added(self) -> None:
        """Jitter should be added to base delay."""
        delays = [get_retry_delay(1) for _ in range(10)]
        # With jitter, delays should vary
        assert len(set(delays)) > 1

    def test_retry_after_header(self) -> None:
        """Retry-After header should be honored."""
        delay = get_retry_delay(1, retry_after_header="10")
        # 10 seconds = 10000 ms
        assert delay == 10000

    def test_invalid_retry_after(self) -> None:
        """Invalid Retry-After should fall back to exponential backoff."""
        delay = get_retry_delay(1, retry_after_header="invalid")
        # Falls back to exponential with jitter: 500-625
        assert 500 <= delay <= 625


class TestGetRetryAfterMs:
    def test_extracts_from_headers(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Rate limited", status=429, headers={"retry-after": "30"})
        result = get_retry_after_ms(err)
        assert result == 30000

    def test_no_retry_after(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Error", status=429)
        result = get_retry_after_ms(err)
        assert result is None


# =============================================================================
# Should Retry Tests
# =============================================================================


class TestShouldRetry:
    def test_retry_on_408(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Timeout", status=408)
        assert should_retry(err) is True

    def test_retry_on_409(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Conflict", status=409)
        assert should_retry(err) is True

    def test_retry_on_429(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Rate limited", status=429)
        assert should_retry(err) is True

    def test_retry_on_529(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Overloaded", status=529)
        assert should_retry(err) is True

    def test_retry_on_401(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Unauthorized", status=401)
        assert should_retry(err) is True

    def test_retry_on_500(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Internal error", status=500)
        assert should_retry(err) is True

    def test_no_retry_on_400(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Bad request", status=400)
        assert should_retry(err) is False

    def test_no_retry_on_404(self) -> None:
        from claude_code.services.api.errors import APIError
        err = APIError("Not found", status=404)
        assert should_retry(err) is False

    def test_persistent_enables_retry(self) -> None:
        """Persistent mode enables retry on 429/529."""
        from claude_code.services.api.errors import APIError
        err = APIError("Rate limited", status=429)
        assert should_retry(err, persistent_enabled=True) is True
