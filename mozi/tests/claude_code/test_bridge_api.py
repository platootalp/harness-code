"""
Tests for bridge/api.py - Bridge API client.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_code.bridge.api import (
    BridgeApiClient,
    BridgeApiDeps,
    BridgeFatalError,
    HeartbeatResponse,
    PermissionResponseEvent,
    WorkData,
    WorkResponse,
    create_bridge_api_client,
    is_expired_error_type,
    is_suppressible_403,
    validate_bridge_id,
)
from claude_code.bridge.config import BridgeConfig, SpawnMode


class TestValidateBridgeId:
    """Tests for validate_bridge_id."""

    def test_valid_alphanumeric(self) -> None:
        """Should accept alphanumeric IDs."""
        result = validate_bridge_id("abc123", "environmentId")
        assert result == "abc123"

    def test_valid_with_underscore(self) -> None:
        """Should accept IDs with underscores."""
        result = validate_bridge_id("env_123_abc", "environmentId")
        assert result == "env_123_abc"

    def test_valid_with_dash(self) -> None:
        """Should accept IDs with dashes."""
        result = validate_bridge_id("env-123-abc", "environmentId")
        assert result == "env-123-abc"

    def test_empty_id_raises(self) -> None:
        """Should raise for empty ID."""
        with pytest.raises(BridgeFatalError) as exc_info:
            validate_bridge_id("", "environmentId")
        assert exc_info.value.status == 400

    def test_none_id_raises(self) -> None:
        """Should raise for None ID."""
        with pytest.raises(BridgeFatalError) as exc_info:
            validate_bridge_id(None, "environmentId")  # type: ignore
        assert exc_info.value.status == 400

    def test_slash_in_id_raises(self) -> None:
        """Should raise for ID with slash (path traversal)."""
        with pytest.raises(BridgeFatalError) as exc_info:
            validate_bridge_id("env/../../../admin", "environmentId")
        assert exc_info.value.status == 400

    def test_dotdot_in_id_raises(self) -> None:
        """Should raise for ID with dotdot."""
        with pytest.raises(BridgeFatalError) as exc_info:
            validate_bridge_id("env..admin", "environmentId")
        assert exc_info.value.status == 400

    def test_special_chars_raises(self) -> None:
        """Should raise for ID with special characters."""
        with pytest.raises(BridgeFatalError) as exc_info:
            validate_bridge_id("env@admin", "environmentId")
        assert exc_info.value.status == 400


class TestIsExpiredErrorType:
    """Tests for is_expired_error_type."""

    def test_expired_in_type(self) -> None:
        """Should return True for 'expired' in error type."""
        assert is_expired_error_type("environment_expired") is True
        assert is_expired_error_type("session_expired") is True

    def test_lifetime_in_type(self) -> None:
        """Should return True for 'lifetime' in error type."""
        assert is_expired_error_type("lifetime_exceeded") is True
        assert is_expired_error_type("token_lifetime") is True

    def test_none_returns_false(self) -> None:
        """Should return False for None."""
        assert is_expired_error_type(None) is False

    def test_no_match_returns_false(self) -> None:
        """Should return False when no match."""
        assert is_expired_error_type("not_found_error") is False
        assert is_expired_error_type("rate_limited") is False


class TestIsSuppressible403:
    """Tests for is_suppressible_403."""

    def test_suppressible_external_poll_sessions(self) -> None:
        """Should suppress 403 for external_poll_sessions scope."""
        err = BridgeFatalError(
            "Access denied: missing scope external_poll_sessions",
            403,
        )
        assert is_suppressible_403(err) is True

    def test_suppressible_environments_manage(self) -> None:
        """Should suppress 403 for environments:manage role."""
        err = BridgeFatalError(
            "Access denied: requires environments:manage",
            403,
        )
        assert is_suppressible_403(err) is True

    def test_non_403_not_suppressible(self) -> None:
        """Should not suppress non-403 errors."""
        err = BridgeFatalError("Not found", 404)
        assert is_suppressible_403(err) is False

    def test_other_403_not_suppressible(self) -> None:
        """Should not suppress other 403 errors."""
        err = BridgeFatalError("Forbidden: general access denied", 403)
        assert is_suppressible_403(err) is False


class TestBridgeFatalError:
    """Tests for BridgeFatalError exception."""

    def test_basic_attributes(self) -> None:
        """BridgeFatalError should have correct attributes."""
        err = BridgeFatalError("test message", 401, "auth_failed")
        assert err.message == "test message"
        assert err.status == 401
        assert err.error_type == "auth_failed"
        assert err.name == "BridgeFatalError"

    def test_without_error_type(self) -> None:
        """BridgeFatalError should work without error_type."""
        err = BridgeFatalError("test message", 500)
        assert err.error_type is None


class TestWorkData:
    """Tests for WorkData dataclass."""

    def test_create(self) -> None:
        """WorkData should create with required fields."""
        data = WorkData(type="session", id="work-123")
        assert data.type == "session"
        assert data.id == "work-123"


class TestWorkResponse:
    """Tests for WorkResponse dataclass."""

    def test_create(self) -> None:
        """WorkResponse should create with required fields."""
        response = WorkResponse(
            id="work-123",
            type="work",
            environment_id="env-456",
            state="pending",
            data=WorkData(type="session", id="sess-789"),
            secret="secret123",
            created_at="2026-04-07T10:00:00Z",
        )
        assert response.id == "work-123"
        assert response.data.type == "session"


class TestHeartbeatResponse:
    """Tests for HeartbeatResponse dataclass."""

    def test_create(self) -> None:
        """HeartbeatResponse should create with required fields."""
        response = HeartbeatResponse(
            lease_extended=True,
            state="running",
            last_heartbeat="2026-04-07T10:05:00Z",
            ttl_seconds=60,
        )
        assert response.lease_extended is True
        assert response.state == "running"
        assert response.ttl_seconds == 60


class TestPermissionResponseEvent:
    """Tests for PermissionResponseEvent dataclass."""

    def test_create_default(self) -> None:
        """PermissionResponseEvent should have sensible defaults."""
        event = PermissionResponseEvent(request_id="req-123")
        assert event.type == "control_response"
        assert event.request_id == "req-123"
        assert event.behavior == "allow"

    def test_to_dict(self) -> None:
        """PermissionResponseEvent should serialize to dict."""
        event = PermissionResponseEvent(request_id="req-123")
        d = event.to_dict()
        assert d["type"] == "control_response"
        assert d["response"]["request_id"] == "req-123"
        assert d["response"]["response"]["behavior"] == "allow"


class TestBridgeApiDeps:
    """Tests for BridgeApiDeps dataclass."""

    def test_create_minimal(self) -> None:
        """BridgeApiDeps should create with minimal fields."""
        deps = BridgeApiDeps(
            base_url="https://api.claude.ai",
            get_access_token=lambda: "token123",
        )
        assert deps.base_url == "https://api.claude.ai"
        assert deps.runner_version == "1.0.0"

    def test_create_full(self) -> None:
        """BridgeApiDeps should accept all optional fields."""
        deps = BridgeApiDeps(
            base_url="https://api.claude.ai",
            get_access_token=lambda: "token123",
            runner_version="2.0.0",
            on_debug=lambda x: None,
            on_auth_401=AsyncMock(),
            get_trusted_device_token=lambda: "device-token",
        )
        assert deps.runner_version == "2.0.0"
        assert deps.get_trusted_device_token() == "device-token"


class TestCreateBridgeApiClient:
    """Tests for create_bridge_api_client factory."""

    def test_defaults(self) -> None:
        """Should use default values."""
        client = create_bridge_api_client()
        assert client.deps.base_url == "https://api.claude.ai"

    def test_custom_base_url(self) -> None:
        """Should accept custom base_url."""
        client = create_bridge_api_client(base_url="https://custom.api.com")
        assert client.deps.base_url == "https://custom.api.com"

    def test_custom_access_token(self) -> None:
        """Should accept custom get_access_token."""
        client = create_bridge_api_client(
            get_access_token=lambda: "custom-token",
        )
        assert client.deps.get_access_token() == "custom-token"

    def test_debug_callback(self) -> None:
        """Should accept debug callback."""
        messages: list[str] = []

        def on_debug(msg: str) -> None:
            messages.append(msg)

        client = create_bridge_api_client(on_debug=on_debug)
        assert client.deps.on_debug is not None


class TestBridgeApiClientAsync:
    """Async tests for BridgeApiClient methods."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Should support async context manager."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )
        async with client as c:
            assert c.deps.base_url == "https://api.claude.ai"
        # Client should be closed
        assert client._client is None

    @pytest.mark.asyncio
    async def test_register_bridge_environment(self) -> None:
        """register_bridge_environment should POST to the correct endpoint."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )
        config = BridgeConfig(
            dir="/home/user/project",
            machine_name="macbook-pro",
            branch="main",
            git_repo_url=None,
            max_sessions=1,
            spawn_mode=SpawnMode.SINGLE_SESSION,
            verbose=False,
            sandbox=False,
            bridge_id="bridge-123",
            worker_type="claw_py",
            environment_id="env-456",
            api_base_url="https://api.claude.ai",
            session_ingress_url="https://api.claude.ai",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "environment_id": "env-new-789",
            "environment_secret": "secret-xyz",
        }

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)
            client._client.aclose = AsyncMock()

            result = await client.register_bridge_environment(config)

            assert result["environment_id"] == "env-new-789"
            assert result["environment_secret"] == "secret-xyz"

    @pytest.mark.asyncio
    async def test_register_bridge_environment_reuse_id(self) -> None:
        """Should include reuseEnvironmentId when set."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )
        config = BridgeConfig(
            dir="/home/user/project",
            machine_name="macbook-pro",
            branch="main",
            git_repo_url=None,
            max_sessions=1,
            spawn_mode=SpawnMode.SINGLE_SESSION,
            verbose=False,
            sandbox=False,
            bridge_id="bridge-123",
            worker_type="claw_py",
            environment_id="env-456",
            api_base_url="https://api.claude.ai",
            session_ingress_url="https://api.claude.ai",
            reuse_environment_id="reuse-123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "environment_id": "env-reused",
            "environment_secret": "secret",
        }

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            await client.register_bridge_environment(config)

            call_kwargs = client._client.post.call_args.kwargs
            assert call_kwargs["json"]["environment_id"] == "reuse-123"

    @pytest.mark.asyncio
    async def test_deregister_environment(self) -> None:
        """deregister_environment should DELETE to the correct endpoint."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.delete = AsyncMock(return_value=mock_response)

            await client.deregister_environment("env-123")

            client._client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_for_work_empty(self) -> None:
        """poll_for_work should return None on empty response."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_response.json.return_value = None

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_response)

            result = await client.poll_for_work("env-123", "secret-456")
            assert result is None

    @pytest.mark.asyncio
    async def test_poll_for_work_with_reclaim(self) -> None:
        """poll_for_work should pass reclaim_older_than_ms param."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = None

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_response)

            await client.poll_for_work("env-123", "secret-456", reclaim_older_than_ms=60000)

            call_kwargs = client._client.get.call_args.kwargs
            assert call_kwargs["params"]["reclaim_older_than_ms"] == 60000

    @pytest.mark.asyncio
    async def test_acknowledge_work(self) -> None:
        """acknowledge_work should POST to the correct endpoint."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            await client.acknowledge_work("env-123", "work-456", "session-token")

            client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat_work(self) -> None:
        """heartbeat_work should return HeartbeatResponse."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "lease_extended": True,
            "state": "running",
            "last_heartbeat": "2026-04-07T10:05:00Z",
            "ttl_seconds": 60,
        }

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            result = await client.heartbeat_work("env-123", "work-456", "session-token")

            assert result.lease_extended is True
            assert result.state == "running"
            assert result.ttl_seconds == 60

    @pytest.mark.asyncio
    async def test_archive_session_409_is_ok(self) -> None:
        """archive_session should handle 409 (already archived) gracefully."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 409

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            # Should not raise
            await client.archive_session("session-123")

    @pytest.mark.asyncio
    async def test_stop_work(self) -> None:
        """stop_work should POST with force parameter."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            await client.stop_work("env-123", "work-456", force=True)

            call_kwargs = client._client.post.call_args.kwargs
            assert call_kwargs["json"]["force"] is True

    @pytest.mark.asyncio
    async def test_send_permission_response_event(self) -> None:
        """send_permission_response_event should POST to the correct endpoint."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.json.return_value = {}

        event = PermissionResponseEvent(request_id="req-123", behavior="allow")

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            await client.send_permission_response_event("session-123", event, "token")

            client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_status_401_raises_fatal(self) -> None:
        """401 should raise BridgeFatalError."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"type": "auth_failed"}}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.delete = AsyncMock(return_value=mock_response)

            with pytest.raises(BridgeFatalError) as exc_info:
                await client.deregister_environment("env-123")
            assert exc_info.value.status == 401

    @pytest.mark.asyncio
    async def test_error_status_403_expired_raises_with_message(self) -> None:
        """403 with expired error should raise with expiry message."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": {"type": "environment_expired"}}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.delete = AsyncMock(return_value=mock_response)

            with pytest.raises(BridgeFatalError) as exc_info:
                await client.deregister_environment("env-123")
            assert exc_info.value.status == 403
            assert "expired" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_error_status_429_raises(self) -> None:
        """429 should raise BridgeFatalError."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.get = AsyncMock(return_value=mock_response)

            with pytest.raises(BridgeFatalError) as exc_info:
                await client.poll_for_work("env-123", "secret")
            assert exc_info.value.status == 429
            assert "Rate limited" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_trusted_device_token_header(self) -> None:
        """Should include X-Trusted-Device-Token when getter returns token."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
                get_trusted_device_token=lambda: "device-token-123",
            )
        )

        headers = client._get_headers("token")
        assert headers["X-Trusted-Device-Token"] == "device-token-123"

    @pytest.mark.asyncio
    async def test_trusted_device_token_header_missing(self) -> None:
        """Should not include X-Trusted-Device-Token when getter returns None."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
                get_trusted_device_token=lambda: None,
            )
        )

        headers = client._get_headers("token")
        assert "X-Trusted-Device-Token" not in headers

    @pytest.mark.asyncio
    async def test_resolve_auth_missing_token(self) -> None:
        """Should raise BridgeFatalError when no token available."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: None,
            )
        )

        with pytest.raises(BridgeFatalError) as exc_info:
            client._resolve_auth()
        assert exc_info.value.status == 401

    @pytest.mark.asyncio
    async def test_reconnect_session(self) -> None:
        """reconnect_session should POST to the correct endpoint."""
        client = BridgeApiClient(
            BridgeApiDeps(
                base_url="https://api.claude.ai",
                get_access_token=lambda: "token",
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch.object(client, "_client", create=True):
            client._client = MagicMock()
            client._client.post = AsyncMock(return_value=mock_response)

            await client.reconnect_session("env-123", "session-456")

            client._client.post.assert_called_once()
