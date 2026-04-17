"""Claude AI OAuth authentication provider for MCP.

TypeScript equivalent: src/services/mcp/auth.ts
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class AuthTokens:
    """OAuth tokens."""

    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None  # Unix timestamp
    token_type: str = "Bearer"


class ClaudeAuthProvider:
    """OAuth authentication provider with auto-refresh.

    Handles OAuth 2.0 authorization code flow with token refresh for MCP servers.
    """

    # Token refresh buffer: refresh if token expires within 5 minutes
    REFRESH_BUFFER_SECONDS = 300

    def __init__(
        self,
        client_id: str,
        client_secret: str | None = None,
        redirect_uri: str = "http://localhost:8080/callback",
    ) -> None:
        """Initialize auth provider.

        Args:
            client_id: OAuth client ID.
            client_secret: Optional OAuth client secret.
            redirect_uri: OAuth redirect URI.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self._tokens: AuthTokens | None = None
        self._refresh_lock = asyncio.Lock()
        self._authorization_url: str | None = None
        self._code_verifier: str | None = None
        self._scopes: str | None = None

    async def get_access_token(self) -> str | None:
        """Get current access token, refreshing if needed.

        Returns:
            Current access token or None if not authenticated.
        """
        if self._tokens is None:
            return None

        await self.refresh_if_needed()
        return self._tokens.access_token

    async def refresh_if_needed(self) -> bool:
        """Refresh token if expired or about to expire.

        Returns:
            True if token was refreshed, False if not needed or failed.
        """
        if self._tokens is None or self._tokens.refresh_token is None:
            return False

        # Check if token is expired or about to expire
        if self._tokens.expires_at is not None:
            time_until_expiry = self._tokens.expires_at - time.time()
            if time_until_expiry > self.REFRESH_BUFFER_SECONDS:
                return False

        # Use lock to prevent concurrent refreshes
        async with self._refresh_lock:
            # Double-check after acquiring lock
            if self._tokens and self._tokens.expires_at:
                if self._tokens.expires_at - time.time() > self.REFRESH_BUFFER_SECONDS:
                    return False

            try:
                await self._do_refresh()
                return True
            except Exception:
                return False

    async def _do_refresh(self) -> None:
        """Perform the actual token refresh."""
        if self._tokens is None or self._tokens.refresh_token is None:
            raise RuntimeError("No refresh token available")

        import urllib.parse as _urllib

        params = _urllib.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self._tokens.refresh_token,
            "client_id": self.client_id,
        })

        if self.client_secret:
            params += f"&client_secret={_urllib.quote(self.client_secret)}"

        # Use asyncio to create a simple HTTP request
        import http.client as _http_client

        # Parse the redirect URI to get host and port
        parsed = _urllib.urlparse(self.redirect_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080

        conn = _http_client.HTTPConnection(host, port)
        try:
            conn.request(
                "POST",
                self.redirect_uri,
                params,
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = conn.getresponse()
            data = response.read().decode()

            if response.status != 200:
                raise Exception(f"Token refresh failed: {response.status} {data}")

            import json
            result = json.loads(data)

            self._tokens = AuthTokens(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", self._tokens.refresh_token),
                expires_at=time.time() + result.get("expires_in", 3600),
                token_type=result.get("token_type", "Bearer"),
            )
        finally:
            conn.close()

    async def authenticate(self, auth_code: str) -> AuthTokens:
        """Exchange authorization code for tokens.

        Args:
            auth_code: The authorization code from the OAuth callback.

        Returns:
            The exchanged auth tokens.
        """
        import http.client as _http_client
        import json
        import urllib.parse as _urllib

        params = _urllib.urlencode({
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
        })

        if self.client_secret:
            params += f"&client_secret={_urllib.quote(self.client_secret)}"
        if self._code_verifier:
            params += f"&code_verifier={self._code_verifier}"

        parsed = _urllib.urlparse(self.redirect_uri)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080

        conn = _http_client.HTTPConnection(host, port)
        try:
            conn.request(
                "POST",
                self.redirect_uri,
                params,
                {"Content-Type": "application/x-www-form-urlencoded"},
            )
            response = conn.getresponse()
            data = response.read().decode()

            if response.status != 200:
                raise Exception(f"Authentication failed: {response.status} {data}")

            result = json.loads(data)

            self._tokens = AuthTokens(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token"),
                expires_at=time.time() + result.get("expires_in", 3600),
                token_type=result.get("token_type", "Bearer"),
            )

            return self._tokens
        finally:
            conn.close()

    async def logout(self) -> None:
        """Clear stored tokens."""
        self._tokens = None
        self._authorization_url = None
        self._code_verifier = None
        self._scopes = None

    def get_authorization_url(self, state: str | None = None) -> str:
        """Get OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.

        Returns:
            The authorization URL to redirect the user to.
        """
        import secrets
        import urllib.parse as _urllib

        # Generate code verifier and challenge for PKCE
        self._code_verifier = secrets.token_urlsafe(64)

        # Simple state generation if not provided
        if state is None:
            state = secrets.token_urlsafe(32)

        params = _urllib.urlencode({
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        })

        if self._scopes:
            params += f"&scope={_urllib.quote(self._scopes)}"

        self._authorization_url = f"{self.redirect_uri}?{params}"
        return self._authorization_url

    def set_scopes(self, scopes: str) -> None:
        """Set OAuth scopes.

        Args:
            scopes: Space-separated list of OAuth scopes.
        """
        self._scopes = scopes

    @property
    def authorization_url(self) -> str | None:
        """Get the OAuth authorization URL.

        Returns:
            The authorization URL if generated, None otherwise.
        """
        return self._authorization_url
