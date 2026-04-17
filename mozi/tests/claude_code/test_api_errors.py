"""
Tests for API error types.
"""

from __future__ import annotations

import pytest

from claude_code.services.api.errors import (
    APIError,
    AuthError,
    PromptTooLongError,
    RateLimitError,
)


class TestAPIError:
    """Tests for APIError base class."""

    def test_create_with_message(self) -> None:
        """Test creating APIError with just a message."""
        err = APIError("Something went wrong")
        assert err.message == "Something went wrong"
        assert err.status is None
        assert str(err) == "Something went wrong"

    def test_create_with_status(self) -> None:
        """Test creating APIError with status code."""
        err = APIError("Not found", status=404)
        assert err.message == "Not found"
        assert err.status == 404

    def test_create_with_headers_and_body(self) -> None:
        """Test creating APIError with headers and body."""
        err = APIError(
            "Server error",
            status=500,
            headers={"x-request-id": "abc123"},
            body="Internal server error",
        )
        assert err.status == 500
        assert err.headers == {"x-request-id": "abc123"}
        assert err.body == "Internal server error"

    def test_repr_basic(self) -> None:
        """Test repr for basic error."""
        err = APIError("test message")
        assert repr(err) == "APIError('test message')"

    def test_repr_with_status(self) -> None:
        """Test repr with status code."""
        err = APIError("test", status=400)
        assert repr(err) == "APIError('test', status=400)"

    def test_inheritance(self) -> None:
        """Test that subclasses can be caught as APIError."""
        err = RateLimitError("rate limited")
        assert isinstance(err, APIError)


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_default_status(self) -> None:
        """Test that status is always 429."""
        err = RateLimitError("Too many requests")
        assert err.status == 429
        assert err.message == "Too many requests"

    def test_with_retry_after(self) -> None:
        """Test with retry_after header."""
        err = RateLimitError(
            "Rate limit exceeded",
            retry_after=60,
            headers={"retry-after": "60"},
        )
        assert err.status == 429
        assert err.retry_after == 60
        assert err.headers == {"retry-after": "60"}

    def test_repr_with_retry_after(self) -> None:
        """Test repr includes retry_after."""
        err = RateLimitError("limited", retry_after=30)
        assert "retry_after=30" in repr(err)

    def test_repr_without_retry_after(self) -> None:
        """Test repr without retry_after."""
        err = RateLimitError("limited")
        assert repr(err) == "RateLimitError('limited')"


class TestAuthError:
    """Tests for AuthError."""

    def test_default_status(self) -> None:
        """Test default status is None."""
        err = AuthError("Invalid API key")
        assert err.status is None
        assert err.message == "Invalid API key"

    def test_with_401(self) -> None:
        """Test with 401 status."""
        err = AuthError("Unauthorized", status=401)
        assert err.status == 401

    def test_with_403(self) -> None:
        """Test with 403 status."""
        err = AuthError("Forbidden", status=403)
        assert err.status == 403

    def test_repr_with_status(self) -> None:
        """Test repr includes status."""
        err = AuthError("auth failed", status=401)
        assert repr(err) == "AuthError('auth failed', status=401)"


class TestPromptTooLongError:
    """Tests for PromptTooLongError."""

    def test_default_status(self) -> None:
        """Test that status is always 400."""
        err = PromptTooLongError("Prompt too long")
        assert err.status == 400
        assert err.message == "Prompt too long"

    def test_with_token_info(self) -> None:
        """Test with token count information."""
        err = PromptTooLongError(
            "Prompt exceeds limit",
            actual_tokens=200000,
            limit_tokens=100000,
        )
        assert err.actual_tokens == 200000
        assert err.limit_tokens == 100000

    def test_token_gap_positive(self) -> None:
        """Test token_gap when over limit."""
        err = PromptTooLongError(
            "Prompt too long",
            actual_tokens=200000,
            limit_tokens=100000,
        )
        assert err.token_gap == 100000

    def test_token_gap_zero(self) -> None:
        """Test token_gap when exactly at limit."""
        err = PromptTooLongError(
            "Prompt at limit",
            actual_tokens=100000,
            limit_tokens=100000,
        )
        assert err.token_gap is None

    def test_token_gap_none_when_missing(self) -> None:
        """Test token_gap returns None when info is missing."""
        err = PromptTooLongError("Prompt too long")
        assert err.token_gap is None

    def test_repr_with_tokens(self) -> None:
        """Test repr includes token info."""
        err = PromptTooLongError(
            "too long",
            actual_tokens=100,
            limit_tokens=50,
        )
        r = repr(err)
        assert "actual_tokens=100" in r
        assert "limit_tokens=50" in r
