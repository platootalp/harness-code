"""Tests for utils/auth.py."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from claude_code.utils.auth import (
    ApiKeyResult,
    ApiKeySource,
    clear_api_key_helper_cache,
    get_anthropic_api_key,
    get_anthropic_api_key_with_source,
    get_auth_token_source,
    get_configured_api_key_helper,
    has_anthropic_api_key_auth,
    is_anthropic_auth_enabled,
)


class TestApiKeySource:
    """Tests for ApiKeySource enum."""

    def test_api_key_source_values(self) -> None:
        assert ApiKeySource.ANTHROPIC_API_KEY == "ANTHROPIC_API_KEY"
        assert ApiKeySource.API_KEY_HELPER == "apiKeyHelper"
        assert ApiKeySource.LOGIN_MANAGED_KEY == "/login managed key"
        assert ApiKeySource.NONE == "none"


class TestApiKeyResult:
    """Tests for ApiKeyResult dataclass."""

    def test_with_key(self) -> None:
        result = ApiKeyResult(key="sk-ant-test", source=ApiKeySource.ANTHROPIC_API_KEY)
        assert result.key == "sk-ant-test"
        assert result.source == ApiKeySource.ANTHROPIC_API_KEY

    def test_with_none_key(self) -> None:
        result = ApiKeyResult(key=None, source=ApiKeySource.NONE)
        assert result.key is None
        assert result.source == ApiKeySource.NONE


class TestIsAnthropicAuthEnabled:
    """Tests for is_anthropic_auth_enabled."""

    def test_env_disabled(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            clear_api_key_helper_cache()
            assert not is_anthropic_auth_enabled()

    def test_env_true(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "true"}):
            assert is_anthropic_auth_enabled()

    def test_env_1(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "1"}):
            assert is_anthropic_auth_enabled()

    def test_env_false(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "false"}):
            assert not is_anthropic_auth_enabled()

    def test_env_yes(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "yes"}):
            assert is_anthropic_auth_enabled()


class TestGetAuthTokenSource:
    """Tests for get_auth_token_source."""

    def test_oauth(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "1"}):
            result = get_auth_token_source()
            assert result["source"] == "oauth"

    def test_env(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            result = get_auth_token_source()
            assert result["source"] == "env"

    def test_helper(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY_HELPER": "/usr/bin/helper"}):
            result = get_auth_token_source()
            assert result["source"] == "helper"
            assert result["helper"] == "/usr/bin/helper"

    def test_none(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = get_auth_token_source()
            assert result["source"] == "none"


class TestHasAnthropicApiKeyAuth:
    """Tests for has_anthropic_api_key_auth."""

    def test_oauth_enabled(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "1"}):
            assert has_anthropic_api_key_auth()

    def test_env_set(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            assert has_anthropic_api_key_auth()

    def test_helper_configured(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY_HELPER": "/bin/helper"}):
            assert has_anthropic_api_key_auth()

    def test_no_source(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert not has_anthropic_api_key_auth()


class TestGetAnthropicApiKeyWithSource:
    """Tests for get_anthropic_api_key_with_source."""

    def test_oauth_returns_none_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_ENABLED": "1"}):
            result = get_anthropic_api_key_with_source()
            assert result.key is None
            assert result.source == ApiKeySource.ANTHROPIC_API_KEY

    def test_env_var(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123"}):
            result = get_anthropic_api_key_with_source()
            assert result.key == "sk-ant-test123"
            assert result.source == ApiKeySource.ANTHROPIC_API_KEY

    def test_skip_helper(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY_HELPER": "/bin/helper"}):
            result = get_anthropic_api_key_with_source(skip_retrieving_key_from_helper=True)
            assert result.key is None
            assert result.source == ApiKeySource.NONE

    def test_no_source(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = get_anthropic_api_key_with_source()
            assert result.key is None
            assert result.source == ApiKeySource.NONE


class TestGetAnthropicApiKey:
    """Tests for get_anthropic_api_key."""

    def test_returns_env_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test456"}):
            key = get_anthropic_api_key()
            assert key == "sk-ant-test456"

    def test_returns_none_when_unavailable(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            key = get_anthropic_api_key()
            assert key is None


class TestGetConfiguredApiKeyHelper:
    """Tests for get_configured_api_key_helper."""

    def test_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            assert get_configured_api_key_helper() is None

    def test_set(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY_HELPER": "/usr/local/bin/akey"}):
            assert get_configured_api_key_helper() == "/usr/local/bin/akey"


class TestClearApiKeyHelperCache:
    """Tests for clear_api_key_helper_cache."""

    def test_clears_cache(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY_HELPER": "/bin/helper"}):
            clear_api_key_helper_cache()
            # Should not raise - just clear state
