"""Env-less bridge timing configuration.

TypeScript equivalent: src/bridge/envLessBridgeConfig.ts
"""

from __future__ import annotations

from dataclasses import dataclass

# =============================================================================
# Types
# =============================================================================


@dataclass
class EnvLessBridgeConfig:
    """Configuration for the env-less (v2) REPL bridge path.

    Attributes:
        init_retry_max_attempts: Max attempts for init-phase retries.
        init_retry_base_delay_ms: Base delay for init retry backoff.
        init_retry_jitter_fraction: Jitter fraction (±fraction) for init retry.
        init_retry_max_delay_ms: Max delay for init retry backoff.
        http_timeout_ms: Axios timeout for POST /sessions, /bridge, /archive.
        uuid_dedup_buffer_size: BoundedUUIDSet ring size (echo + re-delivery dedup).
        heartbeat_interval_ms: CCRClient worker heartbeat cadence.
        heartbeat_jitter_fraction: ±fraction of heartbeat interval per beat.
        token_refresh_buffer_ms: Fire proactive JWT refresh this long before expiry.
        teardown_archive_timeout_ms: Archive POST timeout in teardown().
        connect_timeout_ms: Deadline for onConnect after transport.connect().
        min_version: Semver floor for the env-less bridge path.
        should_show_app_upgrade_message: Whether to nudge users toward app upgrade.
    """

    init_retry_max_attempts: int = 3
    init_retry_base_delay_ms: int = 500
    init_retry_jitter_fraction: float = 0.25
    init_retry_max_delay_ms: int = 4000
    http_timeout_ms: int = 10_000
    uuid_dedup_buffer_size: int = 2000
    heartbeat_interval_ms: int = 20_000
    heartbeat_jitter_fraction: float = 0.1
    token_refresh_buffer_ms: int = 300_000
    teardown_archive_timeout_ms: int = 1500
    connect_timeout_ms: int = 15_000
    min_version: str = "0.0.0"
    should_show_app_upgrade_message: bool = False


# =============================================================================
# Defaults
# =============================================================================

DEFAULT_ENV_LESS_BRIDGE_CONFIG = EnvLessBridgeConfig()


# =============================================================================
# Config Getters
# =============================================================================


async def get_env_less_bridge_config() -> EnvLessBridgeConfig:
    """Fetch the env-less bridge timing config.

    Read once per initEnvLessBridgeCore call — config is fixed for the
    lifetime of a bridge session.

    In the simplified implementation without GrowthBook, this always
    returns the DEFAULT_ENV_LESS_BRIDGE_CONFIG.

    Returns:
        The EnvLessBridgeConfig.
    """
    return DEFAULT_ENV_LESS_BRIDGE_CONFIG


async def check_env_less_bridge_min_version() -> str | None:
    """Check if the current CLI version is below the minimum for env-less bridge.

    In the simplified implementation without GrowthBook, always returns None
    since the min_version defaults to 0.0.0.

    Returns:
        None if version is OK, or an error message string.
    """
    cfg = await get_env_less_bridge_config()
    if cfg.min_version and cfg.min_version != "0.0.0":
        # In a real implementation, would compare with MACRO.VERSION
        return None
    return None


async def should_show_app_upgrade_message() -> bool:
    """Whether to nudge users toward upgrading their claude.ai app.

    In the simplified implementation without GrowthBook, always returns False.

    Returns:
        True if the upgrade nudge should be shown.
    """
    cfg = await get_env_less_bridge_config()
    return cfg.should_show_app_upgrade_message
