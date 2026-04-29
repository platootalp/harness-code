"""
Tests for bridge/env_less.py - Env-less bridge timing configuration.
"""

from __future__ import annotations

import pytest


class TestEnvLessBridgeConfig:
    """Tests for EnvLessBridgeConfig dataclass and defaults."""

    def test_default_values(self) -> None:
        """DEFAULT_ENV_LESS_BRIDGE_CONFIG should have expected values."""
        from claude_code.bridge.env_less import DEFAULT_ENV_LESS_BRIDGE_CONFIG

        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_max_attempts == 3
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_base_delay_ms == 500
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_jitter_fraction == 0.25
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_max_delay_ms == 4000
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.http_timeout_ms == 10_000
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.uuid_dedup_buffer_size == 2000
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.heartbeat_interval_ms == 20_000
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.heartbeat_jitter_fraction == 0.1
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.token_refresh_buffer_ms == 300_000
        assert (
            DEFAULT_ENV_LESS_BRIDGE_CONFIG.teardown_archive_timeout_ms == 1500
        )
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.connect_timeout_ms == 15_000
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.min_version == "0.0.0"
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.should_show_app_upgrade_message is False

    def test_config_creation_with_custom_values(self) -> None:
        """EnvLessBridgeConfig should accept custom values."""
        from claude_code.bridge.env_less import EnvLessBridgeConfig

        cfg = EnvLessBridgeConfig(
            init_retry_max_attempts=5,
            init_retry_base_delay_ms=1000,
            init_retry_jitter_fraction=0.2,
            init_retry_max_delay_ms=8000,
            http_timeout_ms=30_000,
            uuid_dedup_buffer_size=5000,
            heartbeat_interval_ms=30_000,
            heartbeat_jitter_fraction=0.15,
            token_refresh_buffer_ms=600_000,
            teardown_archive_timeout_ms=2000,
            connect_timeout_ms=30_000,
            min_version="1.0.0",
            should_show_app_upgrade_message=True,
        )
        assert cfg.init_retry_max_attempts == 5
        assert cfg.http_timeout_ms == 30_000
        assert cfg.should_show_app_upgrade_message is True


class TestGetEnvLessBridgeConfig:
    """Tests for get_env_less_bridge_config()."""

    @pytest.mark.asyncio
    async def test_returns_default_config(self) -> None:
        """get_env_less_bridge_config returns the default (no GrowthBook)."""
        from claude_code.bridge.env_less import (
            DEFAULT_ENV_LESS_BRIDGE_CONFIG,
            get_env_less_bridge_config,
        )

        cfg = await get_env_less_bridge_config()
        assert cfg.init_retry_max_attempts == DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_max_attempts
        assert cfg.http_timeout_ms == DEFAULT_ENV_LESS_BRIDGE_CONFIG.http_timeout_ms
        assert cfg.heartbeat_interval_ms == DEFAULT_ENV_LESS_BRIDGE_CONFIG.heartbeat_interval_ms


class TestCheckEnvLessBridgeMinVersion:
    """Tests for check_env_less_bridge_min_version()."""

    @pytest.mark.asyncio
    async def test_returns_none_with_default_version(self) -> None:
        """check_env_less_bridge_min_version returns None with 0.0.0 floor."""
        from claude_code.bridge.env_less import (
            check_env_less_bridge_min_version,
        )

        result = await check_env_less_bridge_min_version()
        assert result is None


class TestShouldShowAppUpgradeMessage:
    """Tests for should_show_app_upgrade_message()."""

    @pytest.mark.asyncio
    async def test_returns_false_by_default(self) -> None:
        """should_show_app_upgrade_message returns False (no GrowthBook)."""
        from claude_code.bridge.env_less import (
            should_show_app_upgrade_message,
        )

        result = await should_show_app_upgrade_message()
        assert result is False


class TestTimingValidation:
    """Tests for timing-related value constraints."""

    def test_jitter_fraction_in_valid_range(self) -> None:
        """Jitter fractions should be between 0 and max (0.5)."""
        from claude_code.bridge.env_less import DEFAULT_ENV_LESS_BRIDGE_CONFIG

        assert 0 <= DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_jitter_fraction <= 1
        assert 0 <= DEFAULT_ENV_LESS_BRIDGE_CONFIG.heartbeat_jitter_fraction <= 0.5

    def test_timeout_values_are_positive(self) -> None:
        """All timeout values should be positive."""
        from claude_code.bridge.env_less import DEFAULT_ENV_LESS_BRIDGE_CONFIG

        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.http_timeout_ms > 0
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.connect_timeout_ms > 0
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.teardown_archive_timeout_ms > 0

    def test_retry_config_sensible(self) -> None:
        """Retry config should have max_delay >= base_delay."""
        from claude_code.bridge.env_less import DEFAULT_ENV_LESS_BRIDGE_CONFIG

        assert (
            DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_max_delay_ms
            >= DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_base_delay_ms
        )
        assert DEFAULT_ENV_LESS_BRIDGE_CONFIG.init_retry_max_attempts >= 1
