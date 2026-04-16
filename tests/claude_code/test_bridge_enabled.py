"""
Tests for bridge/enabled.py - Bridge feature gates and entitlement checks.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest


class TestIsBridgeEnabled:
    """Tests for is_bridge_enabled()."""

    def test_returns_true_by_default(self) -> None:
        """is_bridge_enabled should return True (simplified impl)."""
        from claude_code.bridge.enabled import is_bridge_enabled

        assert is_bridge_enabled() is True

    def test_returns_true_regardless_of_env(self) -> None:
        """is_bridge_enabled should return True even without GrowthBook."""
        from claude_code.bridge.enabled import is_bridge_enabled

        with patch.dict("os.environ", {"USER_TYPE": ""}):
            assert is_bridge_enabled() is True


class TestIsEnvLessBridgeEnabled:
    """Tests for is_env_less_bridge_enabled()."""

    def test_returns_false_by_default(self) -> None:
        """is_env_less_bridge_enabled should return False (no GrowthBook)."""
        from claude_code.bridge.enabled import is_env_less_bridge_enabled

        assert is_env_less_bridge_enabled() is False


class TestIsCseShimEnabled:
    """Tests for is_cse_shim_enabled()."""

    def test_returns_true_by_default(self) -> None:
        """is_cse_shim_enabled should return True (shim active by default)."""
        from claude_code.bridge.enabled import is_cse_shim_enabled

        assert is_cse_shim_enabled() is True


class TestCheckBridgeMinVersion:
    """Tests for check_bridge_min_version()."""

    def test_returns_none_by_default(self) -> None:
        """check_bridge_min_version should return None (simplified impl)."""
        from claude_code.bridge.enabled import check_bridge_min_version

        assert check_bridge_min_version() is None


class TestGetCcrAutoConnectDefault:
    """Tests for get_ccr_auto_connect_default()."""

    def test_returns_false_by_default(self) -> None:
        """get_ccr_auto_connect_default should return False."""
        from claude_code.bridge.enabled import get_ccr_auto_connect_default

        assert get_ccr_auto_connect_default() is False


class TestIsCcrMirrorEnabled:
    """Tests for is_ccr_mirror_enabled()."""

    def test_returns_false_by_default(self) -> None:
        """is_ccr_mirror_enabled should return False."""
        from claude_code.bridge.enabled import is_ccr_mirror_enabled

        assert is_ccr_mirror_enabled() is False

    def test_returns_false_regardless_of_env(self) -> None:
        """is_ccr_mirror_enabled should return False even with env var set."""
        from claude_code.bridge.enabled import is_ccr_mirror_enabled

        with patch.dict("os.environ", {"CLAUDE_CODE_CCR_MIRROR": "1"}):
            assert is_ccr_mirror_enabled() is False


class TestAsyncFunctions:
    """Tests for async entitlement functions."""

    @pytest.mark.asyncio
    async def test_is_bridge_enabled_blocking_returns_true(self) -> None:
        """is_bridge_enabled_blocking async wrapper should return True."""
        from claude_code.bridge.enabled import is_bridge_enabled_blocking

        result = await is_bridge_enabled_blocking()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_bridge_disabled_reason_returns_none(self) -> None:
        """get_bridge_disabled_reason should return None (no reason, enabled)."""
        from claude_code.bridge.enabled import get_bridge_disabled_reason

        result = await get_bridge_disabled_reason()
        assert result is None
