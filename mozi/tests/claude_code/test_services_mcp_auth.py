"""Tests for services/mcp/auth.py - ClaudeAuthProvider."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_code.services.mcp.auth import (
    AuthTokens,
    ClaudeAuthProvider,
)


class TestAuthTokens:
    """Tests for AuthTokens dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        tokens = AuthTokens(access_token="abc123")
        assert tokens.access_token == "abc123"
        assert tokens.refresh_token is None
        assert tokens.expires_at is None
        assert tokens.token_type == "Bearer"

    def test_full_tokens(self) -> None:
        """Test tokens with all values."""
        now = time.time()
        tokens = AuthTokens(
            access_token="access",
            refresh_token="refresh",
            expires_at=now + 3600,
            token_type="Bearer",
        )
        assert tokens.access_token == "access"
        assert tokens.refresh_token == "refresh"
        assert tokens.expires_at == now + 3600
        assert tokens.token_type == "Bearer"


class TestClaudeAuthProvider:
    """Tests for ClaudeAuthProvider class."""

    def test_initialization(self) -> None:
        """Test provider initialization."""
        provider = ClaudeAuthProvider(
            client_id="test-client",
            client_secret="secret",
            redirect_uri="http://localhost:8080/callback",
        )
        assert provider.client_id == "test-client"
        assert provider.client_secret == "secret"
        assert provider.redirect_uri == "http://localhost:8080/callback"
        assert provider._tokens is None
        assert provider.REFRESH_BUFFER_SECONDS == 300

    def test_initialization_defaults(self) -> None:
        """Test provider initialization with defaults."""
        provider = ClaudeAuthProvider(client_id="test-client")
        assert provider.client_secret is None
        assert provider.redirect_uri == "http://localhost:8080/callback"

    @pytest.mark.asyncio
    async def test_get_access_token_no_tokens(self) -> None:
        """Test getting token when not authenticated."""
        provider = ClaudeAuthProvider(client_id="test")
        token = await provider.get_access_token()
        assert token is None

    @pytest.mark.asyncio
    async def test_refresh_if_needed_no_tokens(self) -> None:
        """Test refresh check with no tokens."""
        provider = ClaudeAuthProvider(client_id="test")
        result = await provider.refresh_if_needed()
        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_if_needed_no_refresh_token(self) -> None:
        """Test refresh check with no refresh token."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(access_token="abc", refresh_token=None)
        result = await provider.refresh_if_needed()
        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_if_needed_token_valid(self) -> None:
        """Test refresh check when token is still valid."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(
            access_token="abc",
            refresh_token="refresh",
            expires_at=time.time() + 600,  # 10 minutes
        )
        result = await provider.refresh_if_needed()
        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_if_needed_token_expired(self) -> None:
        """Test refresh check when token is expired."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(
            access_token="abc",
            refresh_token="refresh",
            expires_at=time.time() - 100,  # already expired
        )
        # Mock _do_refresh to avoid actual HTTP call
        with patch.object(provider, "_do_refresh", new_callable=AsyncMock) as mock:
            mock.return_value = None
            result = await provider.refresh_if_needed()
            assert result is True
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_if_needed_token_expiring_soon(self) -> None:
        """Test refresh check when token is about to expire."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(
            access_token="abc",
            refresh_token="refresh",
            expires_at=time.time() + 120,  # 2 minutes - within 5 min buffer
        )
        with patch.object(provider, "_do_refresh", new_callable=AsyncMock) as mock:
            mock.return_value = None
            result = await provider.refresh_if_needed()
            assert result is True

    @pytest.mark.asyncio
    async def test_get_access_token_after_auth(self) -> None:
        """Test getting access token after authentication."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(
            access_token="abc123",
            refresh_token="refresh",
            expires_at=time.time() + 3600,
        )
        token = await provider.get_access_token()
        assert token == "abc123"

    @pytest.mark.asyncio
    async def test_logout(self) -> None:
        """Test logout clears tokens."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(access_token="abc", refresh_token="refresh")
        provider._authorization_url = "http://example.com/auth"
        provider._code_verifier = "verifier"
        provider._scopes = "read write"

        await provider.logout()
        assert provider._tokens is None
        assert provider._authorization_url is None
        assert provider._code_verifier is None
        assert provider._scopes is None

    def test_get_authorization_url(self) -> None:
        """Test generating authorization URL."""
        provider = ClaudeAuthProvider(
            client_id="test-client",
            redirect_uri="http://localhost:8080/callback",
        )
        url = provider.get_authorization_url(state="mystate")
        assert "test-client" in url
        assert "mystate" in url
        assert "http://localhost:8080/callback" in url
        assert provider._code_verifier is not None
        assert len(provider._code_verifier) > 0

    def test_get_authorization_url_auto_state(self) -> None:
        """Test authorization URL generates state if not provided."""
        provider = ClaudeAuthProvider(
            client_id="test",
            redirect_uri="http://localhost/callback",
        )
        url = provider.get_authorization_url()
        assert "state=" in url

    def test_get_authorization_url_with_scopes(self) -> None:
        """Test authorization URL includes scopes."""
        provider = ClaudeAuthProvider(client_id="test")
        provider.set_scopes("read write")
        url = provider.get_authorization_url()
        assert "scope=" in url

    def test_set_scopes(self) -> None:
        """Test setting OAuth scopes."""
        provider = ClaudeAuthProvider(client_id="test")
        provider.set_scopes("read write admin")
        assert provider._scopes == "read write admin"

    @pytest.mark.asyncio
    async def test_do_refresh_no_refresh_token(self) -> None:
        """Test _do_refresh fails without refresh token."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(access_token="abc")
        with pytest.raises(RuntimeError, match="No refresh token"):
            await provider._do_refresh()

    def test_authorization_url_property(self) -> None:
        """Test authorization_url property."""
        provider = ClaudeAuthProvider(client_id="test")
        assert provider._authorization_url is None
        # After calling get_authorization_url
        provider.get_authorization_url()
        assert provider.authorization_url is not None


class TestClaudeAuthProviderMockedRefresh:
    """Tests for ClaudeAuthProvider with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_do_refresh_success(self) -> None:
        """Test successful token refresh."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(
            access_token="old-access",
            refresh_token="refresh-token",
            expires_at=time.time() - 100,
        )

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 3600, "token_type": "Bearer"}'

        with patch("http.client.HTTPConnection") as mock_conn_class:
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_response
            mock_conn_class.return_value = mock_conn

            await provider._do_refresh()

            assert provider._tokens is not None
            assert provider._tokens.access_token == "new-access"
            assert provider._tokens.refresh_token == "new-refresh"
            mock_conn.request.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_do_refresh_failure(self) -> None:
        """Test token refresh failure."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._tokens = AuthTokens(
            access_token="old",
            refresh_token="bad-refresh",
            expires_at=time.time() - 100,
        )

        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.read.return_value = b'{"error": "invalid_grant"}'

        with patch("http.client.HTTPConnection") as mock_conn_class:
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_response
            mock_conn_class.return_value = mock_conn

            with pytest.raises(Exception, match="refresh failed"):
                await provider._do_refresh()

    @pytest.mark.asyncio
    async def test_authenticate_success(self) -> None:
        """Test successful authentication with code."""
        provider = ClaudeAuthProvider(client_id="test")
        provider._code_verifier = "test-verifier"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"access_token": "auth-access", "refresh_token": "auth-refresh", "expires_in": 7200, "token_type": "Bearer"}'

        with patch("http.client.HTTPConnection") as mock_conn_class:
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_response
            mock_conn_class.return_value = mock_conn

            tokens = await provider.authenticate("auth-code-123")

            assert tokens.access_token == "auth-access"
            assert tokens.refresh_token == "auth-refresh"
            assert provider._tokens is not None
            assert provider._tokens.access_token == "auth-access"

    @pytest.mark.asyncio
    async def test_authenticate_failure(self) -> None:
        """Test authentication failure."""
        provider = ClaudeAuthProvider(client_id="test")

        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.read.return_value = b'{"error": "invalid_code"}'

        with patch("http.client.HTTPConnection") as mock_conn_class:
            mock_conn = MagicMock()
            mock_conn.getresponse.return_value = mock_response
            mock_conn_class.return_value = mock_conn

            with pytest.raises(Exception, match="Authentication failed"):
                await provider.authenticate("bad-code")
