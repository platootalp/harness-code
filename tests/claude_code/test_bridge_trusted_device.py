"""
Tests for bridge/trusted_device.py - Trusted device enrollment.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestGetTrustedDeviceToken:
    """Tests for get_trusted_device_token()."""

    def test_returns_none_by_default(self) -> None:
        """get_trusted_device_token returns None (no GrowthBook gate)."""
        from claude_code.bridge.trusted_device import get_trusted_device_token

        result = get_trusted_device_token()
        assert result is None

    def test_returns_none_with_env_var(self) -> None:
        """get_trusted_device_token returns None even with env var (simplified impl)."""
        from claude_code.bridge.trusted_device import get_trusted_device_token

        with patch.dict("os.environ", {"CLAUDE_TRUSTED_DEVICE_TOKEN": "dev-token"}):
            result = get_trusted_device_token()
            # Simplified impl returns None
            assert result is None


class TestClearTrustedDeviceToken:
    """Tests for clear_trusted_device_token()."""

    def test_does_not_raise(self) -> None:
        """clear_trusted_device_token should not raise (simplified impl)."""
        from claude_code.bridge.trusted_device import clear_trusted_device_token

        # Should not raise
        clear_trusted_device_token()


class TestEnrollTrustedDevice:
    """Tests for enroll_trusted_device()."""

    @pytest.mark.asyncio
    async def test_does_not_raise(self) -> None:
        """enroll_trusted_device should be best-effort (simplified impl)."""
        from claude_code.bridge.trusted_device import enroll_trusted_device

        # Should not raise
        await enroll_trusted_device()


class TestClearTrustedDeviceTokenCache:
    """Tests for clear_trusted_device_token_cache()."""

    def test_does_not_raise(self) -> None:
        """clear_trusted_device_token_cache should not raise (simplified impl)."""
        from claude_code.bridge.trusted_device import clear_trusted_device_token_cache

        # Should not raise
        clear_trusted_device_token_cache()
