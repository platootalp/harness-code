"""Bridge API client for Remote Control (CCR) operations.

Provides a typed API client for bridge environment registration, work polling,
session management, and heartbeat operations against the CCR backend.

TypeScript equivalent: src/bridge/bridgeApi.ts
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from .config import (
    BRIDGE_LOGIN_INSTRUCTION,
    BridgeConfig,
    get_bridge_access_token,
    get_bridge_base_url,
)

if TYPE_CHECKING:
    pass

# =============================================================================
# Constants
# =============================================================================

BETA_HEADER = "environments-2025-11-01"

# Allowlist pattern for server-provided IDs used in URL path segments.
SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# =============================================================================
# Exceptions
# =============================================================================


class BridgeFatalError(Exception):
    """Fatal bridge errors that should not be retried (e.g. auth failures).

    Attributes:
        status: HTTP status code of the error.
        error_type: Server-provided error type (e.g. "environment_expired").
    """

    def __init__(
        self,
        message: str,
        status: int,
        error_type: str | None = None,
    ) -> None:
        super().__init__(message)
        self.name = "BridgeFatalError"
        self.message = message
        self.status = status
        self.error_type = error_type


# =============================================================================
# Validation
# =============================================================================


def validate_bridge_id(id: str, label: str) -> str:
    """Validate that a server-provided ID is safe to interpolate into a URL path.

    Prevents path traversal (e.g. ../../admin) and injection via IDs that
    contain slashes, dots, or other special characters.

    Args:
        id: The ID to validate.
        label: Human-readable label for error messages.

    Returns:
        The validated ID.

    Raises:
        BridgeFatalError: If the ID contains unsafe characters.
    """
    if not id or not SAFE_ID_PATTERN.match(id):
        raise BridgeFatalError(
            f"Invalid {label}: contains unsafe characters",
            400,
            "invalid_id",
        )
    return id


def is_expired_error_type(error_type: str | None) -> bool:
    """Check whether an error type string indicates a session/environment expiry.

    Args:
        error_type: The error type string to check.

    Returns:
        True if the error type indicates expiry.
    """
    if not error_type:
        return False
    return "expired" in error_type or "lifetime" in error_type


def is_suppressible_403(err: BridgeFatalError) -> bool:
    """Check whether a BridgeFatalError is a suppressible 403 permission error.

    These are 403 errors for scopes like 'external_poll_sessions' or operations
    like StopWork that fail because the user's role lacks 'environments:manage'.
    They don't affect core functionality and shouldn't be shown to users.

    Args:
        err: The BridgeFatalError to check.

    Returns:
        True if this is a suppressible 403 error.
    """
    if err.status != 403:
        return False
    msg = err.message.lower()
    return "external_poll_sessions" in msg or "environments:manage" in msg


# =============================================================================
# Work Response Types
# =============================================================================


@dataclass
class WorkData:
    """Work data payload."""

    type: str  # 'session' | 'healthcheck'
    id: str


@dataclass
class WorkResponse:
    """Work response from the poll endpoint."""

    id: str
    type: str  # 'work'
    environment_id: str
    state: str
    data: WorkData
    secret: str  # base64url-encoded JSON
    created_at: str


@dataclass
class HeartbeatResponse:
    """Heartbeat response from the server."""

    lease_extended: bool
    state: str
    last_heartbeat: str
    ttl_seconds: int


# =============================================================================
# Permission Response Event
# =============================================================================


@dataclass
class PermissionResponseEvent:
    """Permission response event sent back to a session.

    Attributes:
        type: Always 'control_response'.
        request_id: The request ID this responds to.
        response: The permission decision payload.
    """

    type: str = "control_response"
    request_id: str = ""
    behavior: str = "allow"

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dict for JSON serialization."""
        return {
            "type": self.type,
            "response": {
                "subtype": "success",
                "request_id": self.request_id,
                "response": {"behavior": self.behavior},
            },
        }


# =============================================================================
# BridgeApiDeps
# =============================================================================


@dataclass
class BridgeApiDeps:
    """Dependencies for the Bridge API client.

    Attributes:
        base_url: API base URL.
        get_access_token: Callable that returns the OAuth access token or None.
        runner_version: Version string for x-environment-runner-version header.
        on_debug: Optional debug logging callback.
        on_auth_401: Called on 401 to attempt OAuth token refresh.
        get_trusted_device_token: Returns trusted device token for X-Trusted-Device-Token header.
    """

    base_url: str
    get_access_token: Callable[[], str | None]
    runner_version: str = "1.0.0"
    on_debug: Callable[[str], None] | None = None
    on_auth_401: Callable[[str], bool] | None = None
    get_trusted_device_token: Callable[[], str | None] | None = None


# =============================================================================
# BridgeApiClient
# =============================================================================


class BridgeApiClient:
    """Async API client for CCR (Remote Control) bridge operations.

    Provides methods for environment registration, work polling, session
    management, and heartbeat operations.

    Attributes:
        deps: Client dependencies (URLs, auth, callbacks).
    """

    def __init__(self, deps: BridgeApiDeps) -> None:
        self.deps = deps
        self._client: httpx.AsyncClient | None = None

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> BridgeApiClient:
        self._client = httpx.AsyncClient(
            base_url=self.deps.base_url,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _debug(self, msg: str) -> None:
        """Log a debug message if a debug callback is registered."""
        if self.deps.on_debug:
            self.deps.on_debug(msg)

    def _get_headers(self, access_token: str) -> dict[str, str]:
        """Build request headers with auth and beta headers."""
        headers: dict[str, str] = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": BETA_HEADER,
            "x-environment-runner-version": self.deps.runner_version,
        }
        getter = getattr(self.deps, 'get_trusted_device_token', None)
        device_token = getter() if getter else None
        if device_token:
            headers["X-Trusted-Device-Token"] = device_token
        return headers

    def _resolve_auth(self) -> str:
        """Resolve the current access token, raising if not available."""
        token = self.deps.get_access_token()
        if not token:
            raise BridgeFatalError(BRIDGE_LOGIN_INSTRUCTION, 401, "not_authenticated")
        return token

    def _handle_error_status(
        self,
        status: int,
        data: Any,
        context: str,
    ) -> None:
        """Handle HTTP error responses by raising appropriate exceptions."""
        if status == 200 or status == 204:
            return

        detail = _extract_error_detail(data)
        error_type = _extract_error_type(data)

        if status == 401:
            raise BridgeFatalError(
                f"{context}: Authentication failed (401){_detail_suffix(detail)}. {BRIDGE_LOGIN_INSTRUCTION}",
                401,
                error_type,
            )
        if status == 403:
            if is_expired_error_type(error_type):
                msg = (
                    "Remote Control session has expired. "
                    "Please restart with `claude remote-control` or /remote-control."
                )
            else:
                msg = f"{context}: Access denied (403){_detail_suffix(detail)}. Check your organization permissions."
            raise BridgeFatalError(msg, 403, error_type)
        if status == 404:
            msg = detail or f"{context}: Not found (404). Remote Control may not be available for this organization."
            raise BridgeFatalError(msg, 404, error_type)
        if status == 410:
            msg = detail or "Remote Control session has expired. Please restart with `claude remote-control` or /remote-control."
            raise BridgeFatalError(msg, 410, error_type or "environment_expired")
        if status == 429:
            raise BridgeFatalError(f"{context}: Rate limited (429). Polling too frequently.", 429, "rate_limited")
        raise BridgeFatalError(
            f"{context}: Failed with status {status}{_detail_suffix(detail)}",
            status,
            error_type,
        )

    # -------------------------------------------------------------------------
    # Environment Management
    # -------------------------------------------------------------------------

    async def register_bridge_environment(
        self,
        config: BridgeConfig,
    ) -> dict[str, str]:
        """Register this bridge environment with the CCR backend.

        Args:
            config: Bridge configuration including dir, machineName, branch, etc.

        Returns:
            Dict with environment_id and environment_secret.

        Raises:
            BridgeFatalError: On fatal errors (auth failure, not enabled, etc.).
            httpx.HTTPError: On transient network errors.
        """
        self._debug(f"[bridge:api] POST /v1/environments/bridge bridgeId={config.bridge_id}")

        token = self._resolve_auth()
        headers = self._get_headers(token)

        payload: dict[str, Any] = {
            "machine_name": config.machine_name,
            "directory": config.dir,
            "branch": config.branch,
            "git_repo_url": config.git_repo_url,
            "max_sessions": config.max_sessions,
            "metadata": {"worker_type": config.worker_type},
        }
        if config.reuse_environment_id:
            payload["environment_id"] = config.reuse_environment_id

        assert self._client is not None
        response = await self._client.post(
            "/v1/environments/bridge",
            json=payload,
            headers=headers,
            timeout=15.0,
        )

        self._handle_error_status(response.status_code, response.json(), "Registration")
        data: dict[str, str] = response.json()

        self._debug(f"[bridge:api] POST /v1/environments/bridge -> {response.status_code} environment_id={data.get('environment_id')}")
        return data

    async def deregister_environment(self, environment_id: str) -> None:
        """Deregister/delete the bridge environment on graceful shutdown.

        Args:
            environment_id: The environment ID to deregister.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(environment_id, "environmentId")
        self._debug(f"[bridge:api] DELETE /v1/environments/bridge/{environment_id}")

        token = self._resolve_auth()
        headers = self._get_headers(token)

        assert self._client is not None
        response = await self._client.delete(
            f"/v1/environments/bridge/{environment_id}",
            headers=headers,
            timeout=10.0,
        )

        self._handle_error_status(response.status_code, response.json(), "Deregister")
        self._debug(f"[bridge:api] DELETE /v1/environments/bridge/{environment_id} -> {response.status_code}")

    # -------------------------------------------------------------------------
    # Work Polling
    # -------------------------------------------------------------------------

    async def poll_for_work(
        self,
        environment_id: str,
        environment_secret: str,
        signal: Any = None,
        reclaim_older_than_ms: int | None = None,
    ) -> WorkResponse | None:
        """Poll for work items from the CCR backend.

        Args:
            environment_id: The environment ID.
            environment_secret: The environment secret for auth.
            signal: Optional abort signal.
            reclaim_older_than_ms: Reclaim work items older than this many ms.

        Returns:
            WorkResponse if work is available, None otherwise.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(environment_id, "environmentId")

        params: dict[str, Any] | None = None
        if reclaim_older_than_ms is not None:
            params = {"reclaim_older_than_ms": reclaim_older_than_ms}

        assert self._client is not None
        response = await self._client.get(
            f"/v1/environments/{environment_id}/work/poll",
            headers={"Authorization": f"Bearer {environment_secret}"},
            params=params,
            timeout=10.0,
            signal=signal,  # type: ignore[call-arg]
        )

        self._handle_error_status(response.status_code, response.json(), "Poll")

        if response.status_code == 204 or not response.content:
            self._debug(f"[bridge:api] GET .../work/poll -> {response.status_code} (no work)")
            return None

        data = response.json()
        if data is None:
            return None

        self._debug(f"[bridge:api] GET .../work/poll -> {response.status_code} workId={data.get('id')}")
        return _parse_work_response(data)

    async def acknowledge_work(
        self,
        environment_id: str,
        work_id: str,
        session_token: str,
    ) -> None:
        """Acknowledge receipt of a work item.

        Args:
            environment_id: The environment ID.
            work_id: The work item ID.
            session_token: The session token for auth.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(environment_id, "environmentId")
        validate_bridge_id(work_id, "workId")

        self._debug(f"[bridge:api] POST .../work/{work_id}/ack")

        assert self._client is not None
        response = await self._client.post(
            f"/v1/environments/{environment_id}/work/{work_id}/ack",
            headers=self._get_headers(session_token),
            timeout=10.0,
        )

        self._handle_error_status(response.status_code, response.json(), "Acknowledge")
        self._debug(f"[bridge:api] POST .../work/{work_id}/ack -> {response.status_code}")

    async def stop_work(
        self,
        environment_id: str,
        work_id: str,
        force: bool,
    ) -> None:
        """Stop a work item via the environments API.

        Args:
            environment_id: The environment ID.
            work_id: The work item ID.
            force: Whether to force stop.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(environment_id, "environmentId")
        validate_bridge_id(work_id, "workId")

        self._debug(f"[bridge:api] POST .../work/{work_id}/stop force={force}")

        token = self._resolve_auth()
        assert self._client is not None
        response = await self._client.post(
            f"/v1/environments/{environment_id}/work/{work_id}/stop",
            json={"force": force},
            headers=self._get_headers(token),
            timeout=10.0,
        )

        self._handle_error_status(response.status_code, response.json(), "StopWork")
        self._debug(f"[bridge:api] POST .../work/{work_id}/stop -> {response.status_code}")

    async def heartbeat_work(
        self,
        environment_id: str,
        work_id: str,
        session_token: str,
    ) -> HeartbeatResponse:
        """Send a heartbeat for an active work item, extending its lease.

        Args:
            environment_id: The environment ID.
            work_id: The work item ID.
            session_token: The session token for auth.

        Returns:
            HeartbeatResponse with lease_extended and state.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(environment_id, "environmentId")
        validate_bridge_id(work_id, "workId")

        self._debug(f"[bridge:api] POST .../work/{work_id}/heartbeat")

        assert self._client is not None
        response = await self._client.post(
            f"/v1/environments/{environment_id}/work/{work_id}/heartbeat",
            headers=self._get_headers(session_token),
            timeout=10.0,
        )

        self._handle_error_status(response.status_code, response.json(), "Heartbeat")
        data = response.json()

        self._debug(f"[bridge:api] POST .../work/{work_id}/heartbeat -> {response.status_code} lease_extended={data.get('lease_extended')}")
        return HeartbeatResponse(
            lease_extended=data.get("lease_extended", False),
            state=data.get("state", ""),
            last_heartbeat=data.get("last_heartbeat", ""),
            ttl_seconds=data.get("ttl_seconds", 0),
        )

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    async def reconnect_session(
        self,
        environment_id: str,
        session_id: str,
    ) -> None:
        """Force-stop stale worker instances and re-queue a session.

        Used by --session-id to resume a session after the original bridge died.

        Args:
            environment_id: The environment ID.
            session_id: The session ID to reconnect.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(environment_id, "environmentId")
        validate_bridge_id(session_id, "sessionId")

        self._debug(f"[bridge:api] POST .../bridge/reconnect session_id={session_id}")

        token = self._resolve_auth()
        assert self._client is not None
        response = await self._client.post(
            f"/v1/environments/{environment_id}/bridge/reconnect",
            json={"session_id": session_id},
            headers=self._get_headers(token),
            timeout=10.0,
        )

        self._handle_error_status(response.status_code, response.json(), "ReconnectSession")
        self._debug(f"[bridge:api] POST .../bridge/reconnect -> {response.status_code}")

    async def archive_session(self, session_id: str) -> None:
        """Archive a session so it no longer appears as active on the server.

        Idempotent — 409 (already archived) is not treated as an error.

        Args:
            session_id: The session ID to archive.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(session_id, "sessionId")

        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/archive")

        token = self._resolve_auth()
        assert self._client is not None
        response = await self._client.post(
            f"/v1/sessions/{session_id}/archive",
            headers=self._get_headers(token),
            timeout=10.0,
        )

        if response.status_code == 409:
            self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/archive -> 409 (already archived)")
            return

        self._handle_error_status(response.status_code, response.json(), "ArchiveSession")
        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/archive -> {response.status_code}")

    async def send_permission_response_event(
        self,
        session_id: str,
        event: PermissionResponseEvent,
        session_token: str,
    ) -> None:
        """Send a permission response (control_response) to a session.

        Args:
            session_id: The session ID.
            event: The permission response event.
            session_token: The session token for auth.

        Raises:
            BridgeFatalError: On fatal errors.
            httpx.HTTPError: On transient network errors.
        """
        validate_bridge_id(session_id, "sessionId")

        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/events type={event.type}")

        assert self._client is not None
        response = await self._client.post(
            f"/v1/sessions/{session_id}/events",
            json={"events": [event.to_dict()]},
            headers=self._get_headers(session_token),
            timeout=10.0,
        )

        self._handle_error_status(response.status_code, response.json(), "SendPermissionResponseEvent")
        self._debug(f"[bridge:api] POST /v1/sessions/{session_id}/events -> {response.status_code}")


# =============================================================================
# Factory Function
# =============================================================================


def create_bridge_api_client(
    base_url: str | None = None,
    get_access_token: Callable[[], str | None] | None = None,
    runner_version: str = "1.0.0",
    on_debug: Callable[[str], None] | None = None,
    on_auth_401: Callable[[str], bool] | None = None,
    get_trusted_device_token: Callable[[], str | None] | None = None,
) -> BridgeApiClient:
    """Create a new BridgeApiClient with the given dependencies.

    Args:
        base_url: API base URL (defaults to get_bridge_base_url()).
        get_access_token: Callable returning the OAuth access token (defaults to get_bridge_access_token).
        runner_version: Version string for x-environment-runner-version header.
        on_debug: Optional debug logging callback.
        on_auth_401: Called on 401 to attempt OAuth token refresh.
        get_trusted_device_token: Returns trusted device token.

    Returns:
        A configured BridgeApiClient instance.
    """
    deps = BridgeApiDeps(
        base_url=base_url or get_bridge_base_url(),
        get_access_token=get_access_token or get_bridge_access_token,
        runner_version=runner_version,
        on_debug=on_debug,
        on_auth_401=on_auth_401,
        get_trusted_device_token=get_trusted_device_token,
    )
    return BridgeApiClient(deps)


# =============================================================================
# Helpers
# =============================================================================


def _extract_error_detail(data: Any) -> str | None:
    """Extract error detail message from API error response."""
    if data and isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict):
            msg = data["error"].get("message")
            if isinstance(msg, str):
                return msg
        msg = data.get("message")
        if isinstance(msg, str):
            return msg
    return None


def _extract_error_type(data: Any) -> str | None:
    """Extract error type from API error response."""
    if data and isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict):
            typ = data["error"].get("type")
            if isinstance(typ, str):
                return typ
    return None


def _detail_suffix(detail: str | None) -> str:
    """Format a detail string for inclusion in error messages."""
    return f": {detail}" if detail else ""


def _parse_work_response(data: dict[str, Any]) -> WorkResponse:
    """Parse a work response dict into a WorkResponse dataclass."""
    work_data = data.get("data", {})
    return WorkResponse(
        id=data.get("id", ""),
        type=data.get("type", "work"),
        environment_id=data.get("environment_id", ""),
        state=data.get("state", ""),
        data=WorkData(
            type=work_data.get("type", "session"),
            id=work_data.get("id", ""),
        ),
        secret=data.get("secret", ""),
        created_at=data.get("created_at", ""),
    )
