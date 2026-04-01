"""Unit tests for model errors."""

from __future__ import annotations

from mozi.core.model.errors import (
    AuthenticationError,
    CircuitBreakerOpenError,
    InvalidRequestError,
    ModelError,
    ModelInvocationError,
    ModelNotFoundError,
    RateLimitError,
    ResponseParseError,
)


class TestModelError:
    """Tests for base ModelError class."""

    def test_error_code(self) -> None:
        """Test ModelError has error code."""
        error = ModelError("Test error")
        assert hasattr(error, "error_code")
        assert error.error_code is not None

    def test_error_message(self) -> None:
        """Test ModelError message."""
        error = ModelError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self) -> None:
        """Test ModelError inherits from Exception."""
        error = ModelError("Test")
        assert isinstance(error, Exception)


class TestModelInvocationError:
    """Tests for ModelInvocationError."""

    def test_error_code(self) -> None:
        """Test ModelInvocationError has correct error code."""
        error = ModelInvocationError("API call failed")
        assert error.error_code == "MODEL_001"

    def test_error_message(self) -> None:
        """Test ModelInvocationError message."""
        error = ModelInvocationError("Connection timeout")
        assert str(error) == "Connection timeout"

    def test_error_inheritance(self) -> None:
        """Test ModelInvocationError inherits from ModelError."""
        error = ModelInvocationError("Test")
        assert isinstance(error, ModelError)
        assert isinstance(error, Exception)


class TestModelNotFoundError:
    """Tests for ModelNotFoundError."""

    def test_error_code(self) -> None:
        """Test ModelNotFoundError has correct error code."""
        error = ModelNotFoundError("Model not found")
        assert error.error_code == "MODEL_002"

    def test_error_message(self) -> None:
        """Test ModelNotFoundError message."""
        error = ModelNotFoundError("claude-3-opus")
        assert str(error) == "claude-3-opus"


class TestInvalidRequestError:
    """Tests for InvalidRequestError."""

    def test_error_code(self) -> None:
        """Test InvalidRequestError has correct error code."""
        error = InvalidRequestError("Invalid request")
        assert error.error_code == "MODEL_003"


class TestResponseParseError:
    """Tests for ResponseParseError."""

    def test_error_code(self) -> None:
        """Test ResponseParseError has correct error code."""
        error = ResponseParseError("Failed to parse response")
        assert error.error_code == "MODEL_004"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_error_code(self) -> None:
        """Test RateLimitError has correct error code."""
        error = RateLimitError("Rate limit exceeded")
        assert error.error_code == "MODEL_005"


class TestAuthenticationError:
    """Tests for AuthenticationError."""

    def test_error_code(self) -> None:
        """Test AuthenticationError has correct error code."""
        error = AuthenticationError("Authentication failed")
        assert error.error_code == "MODEL_006"


class TestCircuitBreakerOpenError:
    """Tests for CircuitBreakerOpenError."""

    def test_error_code(self) -> None:
        """Test CircuitBreakerOpenError has correct error code."""
        error = CircuitBreakerOpenError()
        assert error.error_code == "MODEL_007"

    def test_default_message(self) -> None:
        """Test CircuitBreakerOpenError default message."""
        error = CircuitBreakerOpenError()
        assert "circuit" in str(error).lower()


class TestAllErrorsHaveCodes:
    """Tests that all errors have unique error codes."""

    def test_all_error_codes_unique(self) -> None:
        """Test all error codes are unique."""
        errors = [
            ModelInvocationError("test"),
            ModelNotFoundError("test"),
            InvalidRequestError("test"),
            ResponseParseError("test"),
            RateLimitError("test"),
            AuthenticationError("test"),
            CircuitBreakerOpenError(),
        ]
        codes = [e.error_code for e in errors]
        assert len(codes) == len(set(codes))

    def test_error_codes_match_expected(self) -> None:
        """Test error codes match expected values."""
        expected_codes = {
            ModelInvocationError: "MODEL_001",
            ModelNotFoundError: "MODEL_002",
            InvalidRequestError: "MODEL_003",
            ResponseParseError: "MODEL_004",
            RateLimitError: "MODEL_005",
            AuthenticationError: "MODEL_006",
            CircuitBreakerOpenError: "MODEL_007",
        }
        for error_class, expected_code in expected_codes.items():
            error = error_class("test")
            assert error.error_code == expected_code
