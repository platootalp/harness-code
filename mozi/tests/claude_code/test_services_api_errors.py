"""
Tests for services/api/errors.py
"""

from __future__ import annotations

import pytest
from claude_code.services.api.errors import (
    APIError,
    API_ERROR_MESSAGE_PREFIX,
    AuthError,
    ConnectionError,
    ConnectionErrorDetails,
    ConnectionTimeoutError,
    PromptTooLongError,
    RateLimitError,
    classify_api_error,
    extract_connection_error_details,
    format_api_error,
    get_errno_code,
    get_errno_path,
    get_ssl_error_hint,
    has_exact_error_message,
    is_enoent,
    is_fs_inaccessible,
    is_media_size_error,
    is_prompt_too_long_message,
    parse_prompt_too_long_token_counts,
    sanitize_message_html,
    starts_with_api_error_prefix,
    to_error,
)


# =============================================================================
# APIError Tests
# =============================================================================


class TestAPIError:
    def test_init_with_message_only(self) -> None:
        err = APIError("something went wrong")
        assert err.message == "something went wrong"
        assert str(err) == "something went wrong"
        assert err.status is None
        assert err.headers is None
        assert err.body is None

    def test_init_with_status(self) -> None:
        err = APIError("bad request", status=400)
        assert err.message == "bad request"
        assert err.status == 400

    def test_init_with_all_fields(self) -> None:
        headers = {"content-type": "application/json"}
        err = APIError(
            "internal error",
            status=500,
            headers=headers,
            body='{"error": "internal"}',
        )
        assert err.message == "internal error"
        assert err.status == 500
        assert err.headers == headers
        assert err.body == '{"error": "internal"}'

    def test_repr_basic(self) -> None:
        err = APIError("oops")
        assert repr(err) == "APIError('oops')"

    def test_repr_with_status(self) -> None:
        err = APIError("not found", status=404)
        assert repr(err) == "APIError('not found', status=404)"

    def test_isinstance_exception(self) -> None:
        err = APIError("fail")
        assert isinstance(err, Exception)

    def test_can_catch_as_api_error(self) -> None:
        with pytest.raises(APIError):
            raise APIError("caught")


# =============================================================================
# RateLimitError Tests
# =============================================================================


class TestRateLimitError:
    def test_init_with_message(self) -> None:
        err = RateLimitError("rate limit exceeded")
        assert err.message == "rate limit exceeded"
        assert err.status == 429
        assert isinstance(err, APIError)
        assert err.retry_after is None

    def test_init_with_retry_after(self) -> None:
        err = RateLimitError("rate limit exceeded", retry_after=60)
        assert err.status == 429
        assert err.retry_after == 60

    def test_init_with_headers_and_body(self) -> None:
        headers = {"retry-after": "120"}
        err = RateLimitError(
            "rate limit exceeded",
            headers=headers,
            body='{"error": "rate_limited"}',
        )
        assert err.headers == headers
        assert err.body == '{"error": "rate_limited"}'

    def test_repr_without_retry_after(self) -> None:
        err = RateLimitError("too many requests")
        assert repr(err) == "RateLimitError('too many requests')"

    def test_repr_with_retry_after(self) -> None:
        err = RateLimitError("too many requests", retry_after=30)
        assert repr(err) == "RateLimitError('too many requests', retry_after=30)"

    def test_isinstance_api_error(self) -> None:
        err = RateLimitError("limit")
        assert isinstance(err, APIError)
        assert isinstance(err, RateLimitError)

    def test_can_catch_as_api_error(self) -> None:
        with pytest.raises(APIError):
            raise RateLimitError("rate limited")


# =============================================================================
# AuthError Tests
# =============================================================================


class TestAuthError:
    def test_init_with_message(self) -> None:
        err = AuthError("invalid api key")
        assert err.message == "invalid api key"
        assert str(err) == "invalid api key"
        assert err.status is None
        assert isinstance(err, APIError)

    def test_init_with_401(self) -> None:
        err = AuthError("unauthorized", status=401)
        assert err.message == "unauthorized"
        assert err.status == 401

    def test_init_with_403(self) -> None:
        err = AuthError("forbidden", status=403)
        assert err.message == "forbidden"
        assert err.status == 403

    def test_init_with_headers(self) -> None:
        headers = {"www-authenticate": "Bearer"}
        err = AuthError("auth required", status=401, headers=headers)
        assert err.headers == headers

    def test_repr_basic(self) -> None:
        err = AuthError("bad key")
        assert repr(err) == "AuthError('bad key')"

    def test_repr_with_status(self) -> None:
        err = AuthError("bad key", status=403)
        assert repr(err) == "AuthError('bad key', status=403)"

    def test_isinstance_api_error(self) -> None:
        err = AuthError("fail")
        assert isinstance(err, APIError)
        assert isinstance(err, AuthError)

    def test_can_catch_as_api_error(self) -> None:
        with pytest.raises(APIError):
            raise AuthError("not authorized")


# =============================================================================
# PromptTooLongError Tests
# =============================================================================


class TestPromptTooLongError:
    def test_init_with_message(self) -> None:
        err = PromptTooLongError("prompt is too long")
        assert err.message == "prompt is too long"
        assert err.status == 400
        assert isinstance(err, APIError)
        assert err.actual_tokens is None
        assert err.limit_tokens is None

    def test_init_with_token_counts(self) -> None:
        err = PromptTooLongError(
            "prompt is too long: 137500 tokens > 135000 maximum",
            actual_tokens=137500,
            limit_tokens=135000,
        )
        assert err.actual_tokens == 137500
        assert err.limit_tokens == 135000

    def test_token_gap_positive(self) -> None:
        err = PromptTooLongError(
            "too long",
            actual_tokens=137500,
            limit_tokens=135000,
        )
        assert err.token_gap == 2500

    def test_token_gap_zero(self) -> None:
        err = PromptTooLongError(
            "exactly at limit",
            actual_tokens=135000,
            limit_tokens=135000,
        )
        assert err.token_gap is None

    def test_token_gap_none_when_not_set(self) -> None:
        err = PromptTooLongError("too long")
        assert err.token_gap is None

    def test_repr_basic(self) -> None:
        err = PromptTooLongError("prompt is too long")
        assert repr(err) == "PromptTooLongError('prompt is too long')"

    def test_repr_with_token_counts(self) -> None:
        err = PromptTooLongError(
            "too long",
            actual_tokens=100,
            limit_tokens=90,
        )
        assert repr(err) == (
            "PromptTooLongError('too long', actual_tokens=100, limit_tokens=90)"
        )

    def test_repr_partial_token_counts(self) -> None:
        err = PromptTooLongError("too long", actual_tokens=100)
        assert repr(err) == (
            "PromptTooLongError('too long', actual_tokens=100)"
        )

    def test_isinstance_api_error(self) -> None:
        err = PromptTooLongError("too long")
        assert isinstance(err, APIError)
        assert isinstance(err, PromptTooLongError)

    def test_can_catch_as_api_error(self) -> None:
        with pytest.raises(APIError):
            raise PromptTooLongError("prompt too long")


# =============================================================================
# ConnectionError Tests
# =============================================================================


class TestConnectionError:
    def test_init_default_message(self) -> None:
        err = ConnectionError()
        assert err.message == "Connection error"
        assert err.code is None

    def test_init_with_message(self) -> None:
        err = ConnectionError("Connection failed")
        assert err.message == "Connection failed"

    def test_init_with_code(self) -> None:
        err = ConnectionError("SSL error", code="CERT_HAS_EXPIRED")
        assert err.code == "CERT_HAS_EXPIRED"

    def test_repr(self) -> None:
        err = ConnectionError("timeout", code="ETIMEDOUT")
        r = repr(err)
        assert "timeout" in r
        assert "ETIMEDOUT" in r


class TestConnectionTimeoutError:
    def test_init_default_message(self) -> None:
        err = ConnectionTimeoutError()
        assert err.message == "Connection timeout"

    def test_init_with_custom_message(self) -> None:
        err = ConnectionTimeoutError("Request timed out after 30s")
        assert err.message == "Request timed out after 30s"


# =============================================================================
# Extract Connection Error Details Tests
# =============================================================================


class TestExtractConnectionErrorDetails:
    def test_extract_from_connection_error_with_code(self) -> None:
        """Test extracting details from ConnectionError with code attribute."""
        err = ConnectionError("timeout", code="ETIMEDOUT")
        details = extract_connection_error_details(err)
        assert details is not None
        assert details.code == "ETIMEDOUT"
        assert details.is_ssl_error is False

    def test_extract_ssl_error(self) -> None:
        """Test extracting SSL error details."""
        err = ConnectionError("SSL cert error", code="CERT_HAS_EXPIRED")
        details = extract_connection_error_details(err)
        assert details is not None
        assert details.is_ssl_error is True

    def test_extract_self_signed_cert(self) -> None:
        """Test extracting self-signed certificate error."""
        err = ConnectionError("self-signed cert", code="DEPTH_ZERO_SELF_SIGNED_CERT")
        details = extract_connection_error_details(err)
        assert details is not None
        assert details.is_ssl_error is True

    def test_extract_hostname_mismatch(self) -> None:
        """Test extracting hostname mismatch error."""
        err = ConnectionError("hostname mismatch", code="HOSTNAME_MISMATCH")
        details = extract_connection_error_details(err)
        assert details is not None
        assert details.is_ssl_error is True

    def test_returns_none_for_none(self) -> None:
        """Test that None input returns None."""
        assert extract_connection_error_details(None) is None

    def test_returns_none_without_code(self) -> None:
        """Test that error without code returns None."""
        err = ConnectionError("error without code")
        assert extract_connection_error_details(err) is None


# =============================================================================
# SSL Error Hint Tests
# =============================================================================


class TestGetSSLErrorHint:
    def test_ssl_error_returns_hint(self) -> None:
        """Test that SSL error returns a hint."""
        err = ConnectionError("SSL error", code="DEPTH_ZERO_SELF_SIGNED_CERT")
        hint = get_ssl_error_hint(err)
        assert hint is not None
        assert "SSL certificate error" in hint
        assert "proxy" in hint.lower()

    def test_non_ssl_error_returns_none(self) -> None:
        """Test that non-SSL error returns None."""
        err = ConnectionError("Connection failed", code="ECONNREFUSED")
        hint = get_ssl_error_hint(err)
        assert hint is None

    def test_timeout_error_returns_none(self) -> None:
        """Test that timeout error returns None."""
        err = ConnectionError("timeout", code="ETIMEDOUT")
        hint = get_ssl_error_hint(err)
        assert hint is None


# =============================================================================
# Sanitize Message HTML Tests
# =============================================================================


class TestSanitizeMessageHTML:
    def test_passes_through_normal_message(self) -> None:
        """Test that normal messages pass through unchanged."""
        msg = "This is a normal error message"
        assert sanitize_message_html(msg) == msg

    def test_extracts_html_title_doctype(self) -> None:
        """Test extracting title from DOCTYPE HTML."""
        html = '<!DOCTYPE html><html><head><title>Error Page</title></head></html>'
        assert sanitize_message_html(html) == "Error Page"

    def test_extracts_html_title_simple(self) -> None:
        """Test extracting title from simple HTML."""
        html = "<html><title>Gateway Error</title></html>"
        assert sanitize_message_html(html) == "Gateway Error"

    def test_empty_html_returns_empty(self) -> None:
        """Test that HTML without title returns empty string."""
        html = "<!DOCTYPE html><html><body>No title</body></html>"
        assert sanitize_message_html(html) == ""

    def test_partial_html_returns_original(self) -> None:
        """Test that partial HTML without title tag returns original."""
        msg = "Some text with <br> and <p> tags"
        assert sanitize_message_html(msg) == msg


# =============================================================================
# Format API Error Tests
# =============================================================================


class TestFormatAPIError:
    def test_connection_timeout(self) -> None:
        """Test formatting connection timeout error."""
        err = ConnectionError("timeout", code="ETIMEDOUT")
        result = format_api_error(err)
        assert "timed out" in result

    def test_ssl_cert_expired(self) -> None:
        """Test formatting SSL certificate expired error."""
        err = ConnectionError("SSL error", code="CERT_HAS_EXPIRED")
        result = format_api_error(err)
        assert "expired" in result

    def test_ssl_verification_failed(self) -> None:
        """Test formatting SSL verification failed error."""
        err = ConnectionError("SSL error", code="UNABLE_TO_VERIFY_LEAF_SIGNATURE")
        result = format_api_error(err)
        assert "verification failed" in result

    def test_ssl_self_signed_cert(self) -> None:
        """Test formatting self-signed certificate error."""
        err = ConnectionError("SSL error", code="SELF_SIGNED_CERT_IN_CHAIN")
        result = format_api_error(err)
        assert "Self-signed" in result

    def test_ssl_hostname_mismatch(self) -> None:
        """Test formatting hostname mismatch error."""
        err = ConnectionError("SSL error", code="HOSTNAME_MISMATCH")
        result = format_api_error(err)
        assert "hostname mismatch" in result

    def test_unknown_error(self) -> None:
        """Test formatting completely unknown error."""
        err = Exception("Unknown error occurred")
        result = format_api_error(err)
        # Unknown errors return fallback message
        assert result == "An unexpected error occurred"


# =============================================================================
# Error Classification Helpers Tests
# =============================================================================


class TestHasExactErrorMessage:
    def test_exact_match(self) -> None:
        """Test exact message match."""
        err = APIError("Exact message")
        assert has_exact_error_message(err, "Exact message") is True

    def test_no_match(self) -> None:
        """Test non-matching message."""
        err = APIError("Different message")
        assert has_exact_error_message(err, "Exact message") is False

    def test_partial_match_returns_false(self) -> None:
        """Test that partial match returns False."""
        err = APIError("This is a longer message")
        assert has_exact_error_message(err, "This is") is False

    def test_none_returns_false(self) -> None:
        """Test that None returns False."""
        assert has_exact_error_message(None, "message") is False


class TestToError:
    def test_exception_passthrough(self) -> None:
        """Test that Exception is returned as-is."""
        original = APIError("Test")
        result = to_error(original)
        assert result is original

    def test_converts_string(self) -> None:
        """Test converting string to Exception."""
        result = to_error("Error string")
        assert isinstance(result, Exception)
        assert str(result) == "Error string"

    def test_converts_none(self) -> None:
        """Test converting None to Exception."""
        result = to_error(None)
        assert isinstance(result, Exception)
        assert str(result) == "None"

    def test_converts_int(self) -> None:
        """Test converting integer to Exception."""
        result = to_error(42)
        assert isinstance(result, Exception)
        assert str(result) == "42"


class TestGetErrnoCode:
    def test_from_dict(self) -> None:
        """Test extracting code from dict."""
        err = {"code": "ENOENT", "message": "Not found"}
        assert get_errno_code(err) == "ENOENT"

    def test_from_object(self) -> None:
        """Test extracting code from object."""
        err = ConnectionError("Test", code="ECONNREFUSED")
        assert get_errno_code(err) == "ECONNREFUSED"

    def test_dict_without_code(self) -> None:
        """Test that dict without code returns None."""
        err = {"message": "Error"}
        assert get_errno_code(err) is None

    def test_none_returns_none(self) -> None:
        """Test that None returns None."""
        assert get_errno_code(None) is None


class TestIsENOENT:
    def test_enoent_returns_true(self) -> None:
        """Test that ENOENT returns True."""
        assert is_enoent({"code": "ENOENT"}) is True

    def test_other_code_returns_false(self) -> None:
        """Test that other codes return False."""
        assert is_enoent({"code": "EACCES"}) is False

    def test_no_code_returns_false(self) -> None:
        """Test that missing code returns False."""
        assert is_enoent({}) is False


class TestGetErrnoPath:
    def test_from_dict(self) -> None:
        """Test extracting path from dict."""
        err = {"code": "ENOENT", "path": "/tmp/missing"}
        assert get_errno_path(err) == "/tmp/missing"

    def test_from_object(self) -> None:
        """Test extracting path from object."""
        err = ConnectionError("Test")
        err.path = "/var/log/file"
        assert get_errno_path(err) == "/var/log/file"

    def test_none_returns_none(self) -> None:
        """Test that None returns None."""
        assert get_errno_path(None) is None


class TestIsFsInaccessible:
    def test_enoent(self) -> None:
        """Test ENOENT is considered inaccessible."""
        assert is_fs_inaccessible({"code": "ENOENT"}) is True

    def test_eacces(self) -> None:
        """Test EACCES is considered inaccessible."""
        assert is_fs_inaccessible({"code": "EACCES"}) is True

    def test_eperm(self) -> None:
        """Test EPERM is considered inaccessible."""
        assert is_fs_inaccessible({"code": "EPERM"}) is True

    def test_enotdir(self) -> None:
        """Test ENOTDIR is considered inaccessible."""
        assert is_fs_inaccessible({"code": "ENOTDIR"}) is True

    def test_eloop(self) -> None:
        """Test ELOOP is considered inaccessible."""
        assert is_fs_inaccessible({"code": "ELOOP"}) is True

    def test_econnreset_returns_false(self) -> None:
        """Test other codes return False."""
        assert is_fs_inaccessible({"code": "ECONNRESET"}) is False

    def test_none_returns_false(self) -> None:
        """Test that None returns False."""
        assert is_fs_inaccessible(None) is False


# =============================================================================
# Parse Prompt Too Long Token Counts Tests
# =============================================================================


class TestParsePromptTooLongTokenCounts:
    def test_parse_counts(self) -> None:
        """Test parsing token counts from message."""
        msg = "prompt is too long: 137500 tokens > 135000 maximum"
        actual, limit = parse_prompt_too_long_token_counts(msg)
        assert actual == 137500
        assert limit == 135000

    def test_parse_case_insensitive(self) -> None:
        """Test parsing is case insensitive."""
        msg = "Prompt Is Too Long: 100 tokens > 50 maximum"
        actual, limit = parse_prompt_too_long_token_counts(msg)
        assert actual == 100
        assert limit == 50

    def test_no_counts_returns_none(self) -> None:
        """Test that missing counts return None."""
        actual, limit = parse_prompt_too_long_token_counts("prompt is too long")
        assert actual is None
        assert limit is None


# =============================================================================
# Is Prompt Too Long Message Tests
# =============================================================================


class TestIsPromptTooLongMessage:
    def test_exact_match(self) -> None:
        """Test exact match."""
        assert is_prompt_too_long_message("Prompt is too long") is True

    def test_case_insensitive(self) -> None:
        """Test case insensitive matching."""
        assert is_prompt_too_long_message("PROMPT IS TOO LONG") is True
        assert is_prompt_too_long_message("prompt is too long") is True

    def test_not_prompt_too_long(self) -> None:
        """Test non-matching message."""
        assert is_prompt_too_long_message("Something else") is False

    def test_longer_message_still_matches(self) -> None:
        """Test that longer message starting with prefix matches."""
        msg = "Prompt is too long: 137500 tokens > 135000 maximum"
        assert is_prompt_too_long_message(msg) is True


# =============================================================================
# Is Media Size Error Tests
# =============================================================================


class TestIsMediaSizeError:
    def test_image_exceeds_maximum(self) -> None:
        """Test detecting image exceeds maximum error."""
        msg = "image exceeds 5 MB maximum: 5316852 bytes > 5242880 bytes"
        assert is_media_size_error(msg) is True

    def test_image_dimensions_exceed(self) -> None:
        """Test detecting image dimensions exceed error."""
        msg = "image dimensions exceed 2000px limit for many-image"
        assert is_media_size_error(msg) is True

    def test_pdf_pages(self) -> None:
        """Test detecting PDF page limit error."""
        msg = "Request rejected: maximum of 100 PDF pages allowed"
        assert is_media_size_error(msg) is True

    def test_pdf_pages_with_number(self) -> None:
        """Test detecting PDF page limit with specific number."""
        msg = "maximum of 50 PDF pages"
        assert is_media_size_error(msg) is True

    def test_not_media_error(self) -> None:
        """Test non-media error returns False."""
        assert is_media_size_error("Connection timeout") is False

    def test_unrelated_image_message(self) -> None:
        """Test that partial image message returns False."""
        msg = "image processing failed"
        assert is_media_size_error(msg) is False


# =============================================================================
# Classify API Error Tests
# =============================================================================


class TestClassifyAPIError:
    def test_rate_limit_error(self) -> None:
        """Test classifying rate limit error."""
        err = RateLimitError("Rate limited")
        result = classify_api_error(err)
        assert result.kind == "rate_limit"
        assert result.status == 429

    def test_auth_error(self) -> None:
        """Test classifying auth error."""
        err = AuthError("Unauthorized", status=401)
        result = classify_api_error(err)
        assert result.kind == "auth_error"
        assert result.status == 401

    def test_connection_error(self) -> None:
        """Test classifying connection error."""
        err = ConnectionError("Connection failed")
        result = classify_api_error(err)
        assert result.kind == "connection_error"

    def test_timeout_error(self) -> None:
        """Test classifying timeout error."""
        err = ConnectionTimeoutError()
        result = classify_api_error(err)
        assert result.kind == "api_timeout"

    def test_ssl_cert_error(self) -> None:
        """Test classifying SSL certificate error."""
        err = ConnectionError("SSL error", code="CERT_HAS_EXPIRED")
        result = classify_api_error(err)
        assert result.kind == "ssl_cert_error"

    def test_server_error_500(self) -> None:
        """Test classifying 500 server error."""
        err = APIError("Internal error", status=500)
        result = classify_api_error(err)
        assert result.kind == "server_error"
        assert result.status == 500

    def test_server_error_503(self) -> None:
        """Test classifying 503 server error."""
        err = APIError("Service unavailable", status=503)
        result = classify_api_error(err)
        assert result.kind == "server_error"

    def test_client_error_400(self) -> None:
        """Test classifying 400 client error."""
        err = APIError("Bad request", status=400)
        result = classify_api_error(err)
        assert result.kind == "client_error"
        assert result.status == 400

    def test_aborted_request(self) -> None:
        """Test classifying aborted request."""
        err = APIError("Request was aborted.")
        result = classify_api_error(err)
        assert result.kind == "aborted"

    def test_unknown_error(self) -> None:
        """Test classifying completely unknown error."""
        err = Exception("Unknown error")
        result = classify_api_error(err)
        assert result.kind == "unknown"

    def test_none_returns_other(self) -> None:
        """Test that None returns 'other' kind."""
        result = classify_api_error(None)
        assert result.kind == "other"


# =============================================================================
# Starts With API Error Prefix Tests
# =============================================================================


class TestStartsWithAPIErrorPrefix:
    def test_starts_with_prefix(self) -> None:
        """Test message starting with API Error prefix."""
        assert starts_with_api_error_prefix("API Error: something went wrong") is True

    def test_starts_with_login_prefix(self) -> None:
        """Test message with login prefix."""
        msg = "Please run /login · API Error: something went wrong"
        assert starts_with_api_error_prefix(msg) is True

    def test_does_not_start_with_prefix(self) -> None:
        """Test message not starting with prefix."""
        assert starts_with_api_error_prefix("Something else happened") is False

    def test_empty_string(self) -> None:
        """Test empty string returns False."""
        assert starts_with_api_error_prefix("") is False


# =============================================================================
# Error Constants Tests
# =============================================================================


class TestErrorConstants:
    def test_api_error_message_prefix(self) -> None:
        """Test API error message prefix constant."""
        assert API_ERROR_MESSAGE_PREFIX == "API Error"


# =============================================================================
# Inheritance Tests
# =============================================================================


class TestErrorInheritance:
    def test_rate_limit_is_api_error(self) -> None:
        assert issubclass(RateLimitError, APIError)

    def test_auth_is_api_error(self) -> None:
        assert issubclass(AuthError, APIError)

    def test_prompt_too_long_is_api_error(self) -> None:
        assert issubclass(PromptTooLongError, APIError)

    def test_connection_is_api_error(self) -> None:
        assert issubclass(ConnectionError, APIError)

    def test_connection_timeout_is_connection(self) -> None:
        assert issubclass(ConnectionTimeoutError, ConnectionError)

    def test_error_hierarchy(self) -> None:
        assert issubclass(RateLimitError, Exception)
        assert issubclass(AuthError, Exception)
        assert issubclass(PromptTooLongError, Exception)
        assert issubclass(ConnectionError, Exception)
        assert issubclass(ConnectionTimeoutError, Exception)

    def test_catch_api_error_catches_all(self) -> None:
        with pytest.raises(APIError):
            raise RateLimitError("rate")

        with pytest.raises(APIError):
            raise AuthError("auth")

        with pytest.raises(APIError):
            raise PromptTooLongError("prompt")

        with pytest.raises(APIError):
            raise ConnectionError("connection")

    def test_catch_connection_catches_timeout(self) -> None:
        with pytest.raises(ConnectionError):
            raise ConnectionTimeoutError("timeout")
