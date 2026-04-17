"""
Tests for bridge/session.py - Session management and crash recovery.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from claude_code.bridge.session import (
    BridgePointer,
    SessionInfo,
    SessionManager,
)

# =============================================================================
# SessionInfo Tests
# =============================================================================


class TestSessionInfo:
    def test_create_minimal(self) -> None:
        """SessionInfo should create with just session_id."""
        info = SessionInfo(session_id="abc-123")
        assert info.session_id == "abc-123"
        assert info.environment_id is None
        assert info.title is None
        assert info.created_at is None

    def test_create_full(self) -> None:
        """SessionInfo should create with all fields."""
        info = SessionInfo(
            session_id="abc-123",
            environment_id="env-456",
            title="My Session",
            created_at="2026-04-07T10:00:00Z",
        )
        assert info.session_id == "abc-123"
        assert info.environment_id == "env-456"
        assert info.title == "My Session"
        assert info.created_at == "2026-04-07T10:00:00Z"


# =============================================================================
# BridgePointer Tests
# =============================================================================


class TestBridgePointer:
    def test_create_minimal(self) -> None:
        """BridgePointer should create with just session_id."""
        ptr = BridgePointer(session_id="abc-123")
        assert ptr.session_id == "abc-123"
        assert ptr.environment_id is None
        assert ptr.source == "repl"

    def test_create_full(self) -> None:
        """BridgePointer should create with all fields."""
        ptr = BridgePointer(
            session_id="abc-123",
            environment_id="env-456",
            source="remote-control",
        )
        assert ptr.session_id == "abc-123"
        assert ptr.environment_id == "env-456"
        assert ptr.source == "remote-control"

    def test_default_source(self) -> None:
        """Default source should be 'repl'."""
        ptr = BridgePointer(session_id="test")
        assert ptr.source == "repl"


# =============================================================================
# SessionManager Tests
# =============================================================================


class TestSessionManagerInit:
    def test_default_base_url(self) -> None:
        """Default base_url should be claude.ai."""
        mgr = SessionManager()
        assert mgr.base_url == "https://api.claude.ai"

    def test_custom_base_url(self) -> None:
        """Should accept custom base_url."""
        mgr = SessionManager(base_url="https://custom.api.com")
        assert mgr.base_url == "https://custom.api.com"

    def test_custom_pointer_dir(self) -> None:
        """Should use custom pointer_dir when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)
            assert mgr._pointer_dir == ptr_dir


class TestSessionManagerCreateSession:
    @pytest.mark.asyncio
    async def test_create_session_returns_info(self) -> None:
        """create_session should return SessionInfo with a UUID."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(
                return_value={
                    "environment_id": "env-789",
                    "title": "Test",
                    "created_at": "2026-04-07T10:00:00Z",
                }
            )
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await mgr.create_session(title="Test")

            assert result.session_id is not None
            assert result.environment_id == "env-789"
            assert result.title == "Test"
            assert result.created_at == "2026-04-07T10:00:00Z"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_without_title(self) -> None:
        """create_session should work without a title."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={})
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await mgr.create_session()

            assert result.session_id is not None
            assert result.title is None
            call_args = mock_client.post.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_create_session_api_failure_returns_local(self) -> None:
        """API failure should return local SessionInfo without raising."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            import httpx

            mock_client = MagicMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
            )
            mock_get.return_value = mock_client

            result = await mgr.create_session(title="Test")

            assert result.session_id is not None
            assert result.title == "Test"
            assert result.created_at is not None


class TestSessionManagerReconnectSession:
    @pytest.mark.asyncio
    async def test_reconnect_returns_session_info(self) -> None:
        """reconnect_session should return SessionInfo."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(
                return_value={"environment_id": "env-456", "title": "Old Session"}
            )
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await mgr.reconnect_session("abc-123", "env-456")

            assert result.session_id == "abc-123"
            assert result.environment_id == "env-456"
            assert result.title == "Old Session"

    @pytest.mark.asyncio
    async def test_reconnect_without_env_id(self) -> None:
        """reconnect_session should work without environment_id."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={})
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            result = await mgr.reconnect_session("abc-123")

            assert result.session_id == "abc-123"


class TestSessionManagerArchiveSession:
    @pytest.mark.asyncio
    async def test_archive_calls_api(self) -> None:
        """archive_session should POST to the archive endpoint."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            await mgr.archive_session("abc-123")

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "abc-123" in str(call_args)
            assert "archive" in str(call_args)

    @pytest.mark.asyncio
    async def test_archive_does_not_raise_on_error(self) -> None:
        """archive_session should not raise on HTTP error."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            import httpx

            mock_client = MagicMock()
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error",
                    request=MagicMock(),
                    response=MagicMock(status_code=500),
                )
            )
            mock_get.return_value = mock_client

            # Should not raise
            await mgr.archive_session("abc-123")


class TestSessionManagerUpdateTitle:
    @pytest.mark.asyncio
    async def test_update_title_calls_api(self) -> None:
        """update_session_title should PUT to the title endpoint."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.put = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            await mgr.update_session_title("abc-123", "New Title")

            mock_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_title_does_not_raise_on_error(self) -> None:
        """update_session_title should not raise on HTTP error."""
        mgr = SessionManager()

        with patch.object(mgr, "_get_client", new_callable=AsyncMock) as mock_get:
            import httpx

            mock_client = MagicMock()
            mock_client.put = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not found",
                    request=MagicMock(),
                    response=MagicMock(status_code=404),
                )
            )
            mock_get.return_value = mock_client

            await mgr.update_session_title("abc-123", "New Title")


# =============================================================================
# Bridge Pointer File Tests
# =============================================================================


class TestWriteBridgePointer:
    def test_write_creates_file(self) -> None:
        """write_bridge_pointer should create the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / ".claude" / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)

            path = mgr.write_bridge_pointer("abc-123", "env-456")

            assert path.exists()
            data = json.loads(path.read_text())
            assert data["sessionId"] == "abc-123"
            assert data["environmentId"] == "env-456"
            assert data["source"] == "repl"

    def test_write_creates_parent_dirs(self) -> None:
        """write_bridge_pointer should create parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / ".claude" / "bridge"
            assert not ptr_dir.exists()

            mgr = SessionManager(pointer_dir=ptr_dir)
            mgr.write_bridge_pointer("abc-123")

            assert ptr_dir.exists()

    def test_write_custom_source(self) -> None:
        """write_bridge_pointer should accept custom source."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)

            mgr.write_bridge_pointer("abc-123", source="remote-control")

            data = json.loads(
                (ptr_dir / "bridge_pointer.json").read_text()
            )
            assert data["source"] == "remote-control"

    def test_write_without_env_id(self) -> None:
        """write_bridge_pointer should work without environment_id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)

            mgr.write_bridge_pointer("abc-123")

            data = json.loads(
                (ptr_dir / "bridge_pointer.json").read_text()
            )
            assert data["sessionId"] == "abc-123"
            assert data["environmentId"] is None

    def test_write_returns_path(self) -> None:
        """write_bridge_pointer should return the file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)

            path = mgr.write_bridge_pointer("abc-123")

            assert path == ptr_dir / "bridge_pointer.json"


class TestReadBridgePointer:
    def test_read_existing_file(self) -> None:
        """read_bridge_pointer should return BridgePointer for existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            ptr_dir.mkdir(parents=True)
            path = ptr_dir / "bridge_pointer.json"
            path.write_text(
                json.dumps({
                    "sessionId": "abc-123",
                    "environmentId": "env-456",
                    "source": "repl",
                })
            )

            mgr = SessionManager(pointer_dir=ptr_dir)
            result = mgr.read_bridge_pointer()

            assert result is not None
            assert result.session_id == "abc-123"
            assert result.environment_id == "env-456"
            assert result.source == "repl"

    def test_read_missing_file(self) -> None:
        """read_bridge_pointer should return None if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge" / "subdir"
            mgr = SessionManager(pointer_dir=ptr_dir)

            result = mgr.read_bridge_pointer()

            assert result is None

    def test_read_invalid_json(self) -> None:
        """read_bridge_pointer should return None for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            ptr_dir.mkdir(parents=True)
            path = ptr_dir / "bridge_pointer.json"
            path.write_text("not valid json {{{")

            mgr = SessionManager(pointer_dir=ptr_dir)
            result = mgr.read_bridge_pointer()

            assert result is None

    def test_read_missing_fields(self) -> None:
        """read_bridge_pointer should handle missing fields gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            ptr_dir.mkdir(parents=True)
            path = ptr_dir / "bridge_pointer.json"
            path.write_text(json.dumps({"sessionId": "abc-123"}))

            mgr = SessionManager(pointer_dir=ptr_dir)
            result = mgr.read_bridge_pointer()

            assert result is not None
            assert result.session_id == "abc-123"
            assert result.environment_id is None
            assert result.source == "repl"


class TestClearBridgePointer:
    def test_clear_removes_file(self) -> None:
        """clear_bridge_pointer should remove the file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            ptr_dir.mkdir(parents=True)
            path = ptr_dir / "bridge_pointer.json"
            path.write_text(json.dumps({"sessionId": "abc-123"}))

            mgr = SessionManager(pointer_dir=ptr_dir)
            mgr.clear_bridge_pointer()

            assert not path.exists()

    def test_clear_nonexistent_file(self) -> None:
        """clear_bridge_pointer should not raise if file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)

            # Should not raise
            mgr.clear_bridge_pointer()


class TestGetPointerPath:
    def test_returns_correct_path(self) -> None:
        """get_pointer_path should return the expected file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ptr_dir = Path(tmpdir) / "bridge"
            mgr = SessionManager(pointer_dir=ptr_dir)

            path = mgr.get_pointer_path()

            assert path == ptr_dir / "bridge_pointer.json"


class TestSessionManagerCloseClient:
    @pytest.mark.asyncio
    async def test_close_owned_client(self) -> None:
        """_close_client should close client if we own it."""
        mgr = SessionManager()

        await mgr._get_client()
        assert mgr._owned_client is True

        await mgr._close_client()

        assert mgr._http_client is None
        assert mgr._owned_client is False

    @pytest.mark.asyncio
    async def test_close_does_not_close_external_client(self) -> None:
        """_close_client should not close externally-provided client."""
        external = MagicMock()
        mgr = SessionManager(http_client=external)

        await mgr._close_client()

        assert mgr._http_client is external
        assert not mgr._owned_client
